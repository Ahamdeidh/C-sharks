# Lunar Navigator — UX Redesign Plan

## Goal
إعادة بناء واجهة Lunar Navigator من الصفر بصريًا لتصبح أسهل للفهم واتخاذ القرار، مع الحفاظ على منطق المحاكاة والشفافية العلمية الموجودة.

## Design
- **Design movement:** هدوء بصري مستوحى من غرف العمليات الحديثة، مع طبقات evidence-first واضحة.
- **Core principles:** مسار قرار واضح، أقل ازدحام، حالة النظام مرئية، وتحذير علمي صريح دون تشويش.
- **Color philosophy:** الأزرق السماوي للبيانات والإجراء الأساسي، الأخضر للحالة المتصلة/المتحققة، والعنبر للقيود أو الحاجة للمراجعة.
- **Layout paradigm:** شريط إعدادات يساري ثابت ومساحة عمل متدفقة تبدأ بملخص قرار كبير ثم النتائج من الأعلى إلى الأسفل.
- **Signature elements:** Mission Overview في أعلى الشاشة، شارات الحالة، وبطاقات KPI ذات مصدر وحدود ظاهرة.
- **Interaction philosophy:** المستخدم يضبط المدخلات ثم يرى مباشرة ماذا سيحدث، ما حالة التشغيل، وهل النتيجة متزامنة مع الإعدادات.
- **Animation:** حركات قصيرة وهادئة للحالة والأزرار فقط؛ لا توجد حركة زخرفية تنافس البيانات.
- **Typography system:** Manrope للعناوين والقراءة، DM Mono للقيم والحالات التقنية.
- **Brand essence:** أداة فرز وتخطيط شفافة لفرق مهمات القطب الجنوبي للقمر؛ عملية، صريحة، وقابلة للتدقيق.
- **Brand voice:** عملية ودقيقة؛ “Run one transparent simulation.” و “Use this as a triage brief, not a landing certificate.”
- **Signature brand color:** cyan `#67E8F9` كإشارة مميزة للملاحة والبيانات.

## Implementation
1. Preserve existing simulation, provenance, comparison, export, and analysis panels.
2. Replace the global visual system with a calm command-center palette, spacing scale, responsive rules, and clearer hierarchy.
3. Add a decision-first Mission Overview block that summarizes target, duration, engine state, and the primary action.
4. Keep `.env` value-free so deployment values can be supplied later.
5. Validate with production build and existing test suite.
