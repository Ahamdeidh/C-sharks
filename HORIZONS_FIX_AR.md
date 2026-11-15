# إصلاح اتصال JPL Horizons — Lunar Landing Site Navigator

## سبب التوقف

في نسخة المشروع التي شاركتها، المتغير `ENABLE_LIVE_HORIZONS` موجود في `.env` لكنه بلا قيمة. والأهم أن التطبيق يقرأه من **بيئة عملية الخادم** عبر `os.getenv`؛ تشغيل `uvicorn` من مجلد `backend` لا يحمّل تلقائياً ملف `.env` الموجود بجذر المشروع. لذلك قد يعمل التطبيق على fixture مسجّل فقط، أو لا يجد بيانات تغطي الموقع والفترة المطلوبين. الكود يطلب Horizons الحي فقط عندما تكون قيمة المتغير `1` أو `true` أو `yes`.

## التشغيل المحلي الموصى به

أضفت `backend/run_with_live_horizons.sh` ليضبط المتغير قبل تشغيل FastAPI، مع إبقاء المنفذ الافتراضي 8000. من مجلد المشروع شغّله هكذا:

```bash
chmod +x backend/run_with_live_horizons.sh
./backend/run_with_live_horizons.sh
```

ثم في نافذة طرفية ثانية، شغّل الواجهة الأمامية:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

على Windows PowerShell، شغّل الخادم من مجلد `backend`:

```powershell
$env:ENABLE_LIVE_HORIZONS = "1"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

وفي نافذة ثانية من مجلد المشروع:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

إذا كان الخادم مستضافاً في مكان آخر، اضبط `ENABLE_LIVE_HORIZONS=1` في **إعدادات خدمة الـBackend نفسها** ثم أعد تشغيلها. واضبط `VITE_API_BASE_URL` وقت بناء الواجهة إلى عنوان Backend العام الصحيح؛ هذا المتغير منفصل عن تفعيل Horizons.

## فحص سريع

1. افتح `http://127.0.0.1:8000/health` إن كان هذا المسار مفعلاً، أو `http://127.0.0.1:8000/docs` للتأكد من أن FastAPI استجاب.
2. نفّذ محاكاة للموقع والتاريخ المطلوبين من الواجهة.
3. في نتيجة المحاكاة، افحص `ephemeris_check.source`. المطلوب عند نجاح الاستعلام هو `jpl_horizons_live`، ويجب أن يعرض `coverage.steps_with_real_ephemeris` خطوات فعلية.
4. إذا تعذر الوصول إلى JPL، سيسجل الخادم سبباً في سجله ويحاول الرجوع إلى fixture المطابقة. لا تُعامل fixture على أنها تغطية لتاريخ أو إحداثيات أخرى.

يمكن تجربة API الرسمية مباشرةً من الطرفية لطلب مثال قصير للشمس عند راصد قمري. تغيير `COMMAND` إلى `399` يطلب الأرض:

```bash
curl -G 'https://ssd.jpl.nasa.gov/api/horizons.api' \
  --data-urlencode 'format=json' \
  --data-urlencode "EPHEM_TYPE='OBSERVER'" \
  --data-urlencode "COMMAND='10'" \
  --data-urlencode "CENTER='coord@301'" \
  --data-urlencode "COORD_TYPE='GEODETIC'" \
  --data-urlencode "SITE_COORD='0,-89.9,4.2'" \
  --data-urlencode "START_TIME='2026-11-15 14:00'" \
  --data-urlencode "STOP_TIME='2026-11-16 14:00'" \
  --data-urlencode "STEP_SIZE='6 h'" \
  --data-urlencode "QUANTITIES='4'" \
  --data-urlencode "ANG_FORMAT='DEG'" \
  --data-urlencode "CSV_FORMAT='YES'"
```

استخدم `curl` أو عميل HTTP يشفّر المعاملات؛ لا تركّب URL يدوياً مع مسافات وفواصل غير مشفّرة. واجهة Horizons الرسمية تدعم GET وPOST. وفي طلبات JSON، افحص وجود `error` قبل استخدام `result`، وافحص توقيع `signature.version` عند بناء محلّل يعتمد على تنسيق الاستجابة.

## ما تم التحقق منه

جرّبت الاتصال الفعلي بعنوان NASA/JPL الرسمي. أعاد HTTP 200 وتوقيع API بالإصدار `1.2`، من دون حقل خطأ. كما استُخدم منشئ الطلبات الموجود في المشروع نفسه لطلب سمت وارتفاع الشمس `COMMAND=10` والأرض `COMMAND=399` من مركز `coord@301` عند إحداثيات Shackleton (`lat=-89.9`, `lon=0`, ارتفاع الراصد `4.2 km`) للفترة 15–16 نوفمبر 2026. نجح الطلبان وأعاد كل منهما خمس عينات على خطوة الست ساعات.

لم أغيّر إعدادات أو ملفات Drive الأصلية؛ الملف المرفق هو إضافة تشغيل يمكن وضعها داخل نسخة المشروع. الاختبار أعلاه يثبت اتصال Horizons ومعاملات الاستعلام، لكنه لا يثبت إعداد استضافة الـBackend لديك أو عنوانه العام.

## تنبيهات علمية مهمة

Horizons يعطي هنا زوايا ظاهرية للراصد. لوحة المشروع تقارن الارتفاع بالأفق المحلي فقط؛ ذلك ليس بحد ذاته تحققاً من قناع التضاريس أو خط رؤية الاتصالات أو سلامة موقع الهبوط. كما أن وصول الاستعلام الحي لا يحل تلقائياً قيود تغطية DEM أو مطابقة الإحداثيات والارتفاع أو صلاحية النماذج الأخرى. أبقِ مصدر البيانات والتغطية ظاهرين في نتائج المشروع.

## مصادر NASA/JPL

- [صفحة Horizons الرئيسية](https://ssd.jpl.nasa.gov/horizons/)
- [مرجع API الرسمي ومعاملات GET](https://ssd-api.jpl.nasa.gov/doc/horizons.html)
- [مرجع API الرسمي لملف POST](https://ssd-api.jpl.nasa.gov/doc/horizons_file.html)
- [شرح استخدام الواجهة والنتائج](https://ssd.jpl.nasa.gov/horizons/tutorial.html)
