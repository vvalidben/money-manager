"""Arabic translations: English text (a ``str.format`` template) -> Arabic.

Generated from the interface text; ``tests/test_i18n.py`` checks that every text
has a translation with the same placeholders."""

CATALOG: dict[str, str] = {
    "\n(to date)":
        "\n(حتى اليوم)",
    "\nLoans: {0}":
        "\nالقروض: {0}",
    "\n… and {0} more.":
        "\n… و{0} أخرى.",
    " (out of date)":
        " (غير محدّثة)",
    " (protected by your password)":
        " (محمية بكلمة المرور)",
    " (the transaction type decides whether money comes in or goes out)":
        " (نوع العملية هو الذي يحدد دخول المال أو خروجه)",
    " (to date)":
        " (حتى اليوم)",
    " ({0} of average monthly spending)":
        " ({0} من متوسط المصاريف الشهرية)",
    " ({0}, newer vs older half)":
        " ({0}، النصف الأحدث مقابل الأقدم)",
    " Add an Anthropic API key in Settings first.":
        " أضف أولاً مفتاح API من Anthropic في الإعدادات.",
    " Its expense will be deleted too and your balance recalculated.":
        " سيتم حذف مصروفه أيضاً وإعادة حساب رصيدك.",
    " · adjustments and transfers {0}":
        " · التسويات والتحويلات {0}",
    " · showing the first {0} lines":
        " · عرض أول {0} سطر",
    " · The answer was cut off at the length limit.":
        " · تم قطع الإجابة عند الحد الأقصى للطول.",
    " · {0} overdue":
        " · {0} متأخرة",
    " · {0} sorted by your category rules":
        " · {0} صُنّفت حسب قواعد الفئات",
    "! Behind":
        "! متأخر عن الوتيرة",
    "! Needs attention":
        "! يحتاج إلى انتباه",
    "! Overdue":
        "! تجاوز الموعد",
    "'{0}' has more than two decimals":
        "«{0}» يحتوي على أكثر من رقمين عشريين",
    "'{0}' is ambiguous: write 1200 or 1 200 for thousands, or 1.20 for decimals.":
        "«{0}» غامض: اكتب 1200 أو 1 200 للآلاف، أو 1.20 للكسور العشرية.",
    "'{0}' is an income category; subscriptions need an expense category.":
        "«{0}» فئة مداخيل؛ الاشتراكات تحتاج إلى فئة مصاريف.",
    "'{0}' is an {1} category and cannot be used for an {2} transaction.":
        "«{0}» فئة {1} ولا يمكن استخدامها لعملية {2}.",
    "'{0}' is archived; restore it first.":
        "«{0}» مؤرشف؛ استعده أولاً.",
    "'{0}' is not a date.":
        "«{0}» ليس تاريخاً.",
    "'{0}' is not a valid amount.":
        "«{0}» ليس مبلغاً صالحاً.",
    "'{0}' is not an amount":
        "«{0}» ليس مبلغاً",
    "'{0}' is not an investment category. Mark it as one (Statistics → Investment categories) or choose another.":
        "«{0}» ليست فئة استثمار. حدّدها كذلك (الإحصائيات ← فئات الاستثمار) أو اختر فئة أخرى.",
    "'{0}' is not an {1} category.":
        "«{0}» ليست فئة {1}.",
    "'{0}' is paused; resume it first.":
        "«{0}» متوقف مؤقتاً؛ استأنفه أولاً.",
    "'{0}' is reserved for money that is not allocated.":
        "«{0}» محجوز للمال غير المخصص.",
    "'{0}.{1}' has a value of the wrong type.":
        "«{0}.{1}» يحتوي على قيمة من نوع خاطئ.",
    "'{0}.{1}' is missing a value.":
        "«{0}.{1}» تنقصه قيمة.",
    "(no description)":
        "(بدون وصف)",
    "(processed on this computer).":
        "(تمت المعالجة على هذا الحاسوب).",
    "(sent to Anthropic).":
        "(أُرسل إلى Anthropic).",
    "(to date)":
        "(حتى اليوم)",
    "0.00 (optional)":
        "0,00 (اختياري)",
    "1 receipt attached":
        "إيصال واحد مرفق",
    "1 recorded":
        "سُجّلت واحدة",
    "1 recurring entry recorded":
        "سُجّلت عملية متكررة واحدة",
    "1 year":
        "سنة",
    "12/31/2026 (month first)":
        "12/31/2026 (الشهر أولاً)",
    "3 months":
        "3 أشهر",
    "30 days":
        "30 يوماً",
    "6 months":
        "6 أشهر",
    "7 days":
        "7 أيام",
    "A backup contains all of your data: accounts, transactions, allocations, goals, subscriptions, investments, settings and the AI insight history. It is a readable JSON file that restores everything exactly. API keys are never included.":
        "تحتوي النسخة الاحتياطية على كل بياناتك: الحسابات والعمليات والمخصصات والأهداف والاشتراكات والاستثمارات والإعدادات وسجل تحليلات الذكاء الاصطناعي. إنها ملف JSON مقروء يستعيد كل شيء بدقة. مفاتيح API لا تُضمَّن أبداً.",
    "A custom range has no preset dates.":
        "الفترة المخصصة ليس لها تواريخ محددة مسبقاً.",
    "A goal named '{0}' already exists.":
        "يوجد هدف باسم «{0}» مسبقاً.",
    "A key ending in {0} is stored in {1}.":
        "مفتاح ينتهي بـ {0} محفوظ في {1}.",
    "A loan repayment is due":
        "حان موعد سداد قرض",
    "A loan should be repaid to you":
        "يجب أن يُردّ إليك قرض",
    "A local model must run on this computer (localhost or 127.0.0.1). Use the online provider for remote services.":
        "يجب أن يعمل النموذج المحلي على هذا الحاسوب (localhost أو 127.0.0.1). استخدم المزود عبر الإنترنت للخدمات البعيدة.",
    "A recurring entry could not be recorded":
        "تعذّر تسجيل عملية متكررة",
    "A repayment cannot be dated before the debt started.":
        "لا يمكن أن يكون تاريخ السداد قبل بداية الدين.",
    "a row in '{0}' is malformed.":
        "سطر في «{0}» غير سليم.",
    "A safety backup was saved to:\n{0}":
        "تم حفظ نسخة أمان في:\n{0}",
    "A single {0} expense of {1} on {2} is {3}x the typical expense of {4}.":
        "مصروف واحد من {0} بقيمة {1} في {2} يساوي {3} مرة المصروف المعتاد البالغ {4}.",
    "A subscription is a reminder: payments are only recorded when you confirm them, so your balance never changes on its own.":
        "الاشتراك تذكير: لا تُسجَّل الدفعات إلا عند تأكيدها، لذلك لا يتغير رصيدك من تلقاء نفسه.",
    "A subscription named '{0}' already exists.":
        "يوجد اشتراك باسم «{0}» مسبقاً.",
    "A transaction can have at most {0} receipts.":
        "يمكن أن تحتوي العملية على {0} إيصالات كحد أقصى.",
    "A transfer moves money between two of your accounts. Add the other account first (New account), e.g. your cash or a card.":
        "التحويل ينقل المال بين حسابين من حساباتك. أضف الحساب الآخر أولاً (حساب جديد)، مثل نقودك أو بطاقة.",
    "A withdrawal lowers the amount invested. It does not change your balance: if the money came back to one of your accounts, record that as a transaction too.":
        "السحب يخفض المبلغ المستثمر. لا يغير رصيدك: إذا عاد المال إلى أحد حساباتك، فسجّل ذلك أيضاً كعملية.",
    "About Money Manager":
        "حول Money Manager",
    "About {0} per month in {1} {2} (detected from the last 12 months)":
        "حوالي {0} شهرياً في {1} {2} (مكتشفة من آخر 12 شهراً)",
    "Account":
        "الحساب",
    "Account '{0}' uses {1}; allocations are kept in {2}.":
        "الحساب «{0}» يستخدم {1}؛ المخصصات محفوظة بـ {2}.",
    "Account '{0}' uses {1}; the {2} reports in {3}.":
        "الحساب «{0}» يستخدم {1}؛ {2} يُعرض بـ {3}.",
    "Account created":
        "تم إنشاء الحساب",
    "Account deleted":
        "تم حذف الحساب",
    "Account updated":
        "تم تعديل الحساب",
    "Account {0!r} does not exist.":
        "الحساب {0!r} غير موجود.",
    "Accounts":
        "الحسابات",
    "Accounts below zero (e.g. cards)":
        "حسابات تحت الصفر (مثل البطاقات)",
    "Accounts in credit":
        "حسابات دائنة",
    "Across all budgets":
        "عبر كل الميزانيات",
    "Active":
        "نشطة",
    "Active goals":
        "الأهداف الجارية",
    "Active subscriptions":
        "الاشتراكات النشطة",
    "Active subscriptions only":
        "الاشتراكات النشطة فقط",
    "Actual balance today":
        "الرصيد الفعلي اليوم",
    "Add a second account":
        "أضف حساباً ثانياً",
    "Add a second account (New account) to transfer between them":
        "أضف حساباً ثانياً (حساب جديد) للتحويل بينهما",
    "Add another account, e.g. cash or a card":
        "أضف حساباً آخر، مثل النقود أو بطاقة",
    "Add contribution":
        "إضافة مساهمة",
    "Add investment":
        "إضافة استثمار",
    "Add money":
        "إضافة مال",
    "Add money to {0}":
        "إضافة مال إلى {0}",
    "Add Netflix, your phone plan, internet or any other regular payment to see what they cost per month and when the next ones are due.":
        "أضف Netflix أو اشتراك هاتفك أو الإنترنت أو أي دفعة منتظمة أخرى لترى كلفتها الشهرية ومواعيد الدفعات القادمة.",
    "Add rule":
        "إضافة قاعدة",
    "Add rule…":
        "إضافة قاعدة…",
    "Add subscription":
        "إضافة اشتراك",
    "Add the account you want to track first.":
        "أضف أولاً الحساب الذي تريد متابعته.",
    "Add transaction":
        "إضافة عملية",
    "Add transaction (Ctrl+N)":
        "إضافة عملية (Ctrl+N)",
    "Add…":
        "إضافة…",
    "Adjustment (+)":
        "تسوية (+)",
    "Adjustment (−)":
        "تسوية (−)",
    "Adjustments":
        "التسويات",
    "Advisor answer":
        "إجابة المستشار",
    "AES-256 encryption. Without the password the backup cannot be opened — a forgotten password cannot be recovered.":
        "تشفير AES-256. بدون كلمة المرور لا يمكن فتح النسخة الاحتياطية — ولا يمكن استرجاع كلمة مرور منسية.",
    "After 1 minute without use":
        "بعد دقيقة واحدة دون استخدام",
    "After {0} minutes without use":
        "بعد {0} دقائق دون استخدام",
    "AI Advisor":
        "المستشار الذكي",
    "AI answers interpret the figures calculated above and can be wrong. Numbers in the answer are checked against your data; check anything important yourself.":
        "إجابات الذكاء الاصطناعي تفسر الأرقام المحسوبة أعلاه وقد تخطئ. يتم التحقق من الأرقام الواردة في الإجابة مقابل بياناتك؛ تحقق بنفسك من كل ما هو مهم.",
    "AI assistant":
        "المساعد الذكي",
    "AI features are off.":
        "ميزات الذكاء الاصطناعي متوقفة.",
    "AI features are optional and off unless you choose a provider. They receive a summary calculated by Money Manager, never your database, transaction descriptions or account names.":
        "ميزات الذكاء الاصطناعي اختيارية ومتوقفة ما لم تختر مزوداً. تتلقى ملخصاً يحسبه Money Manager، وليس قاعدة بياناتك أو أوصاف العمليات أو أسماء الحسابات أبداً.",
    "AI insights are optional":
        "تحليلات الذكاء الاصطناعي اختيارية",
    "AI is off. Choose a local or online provider above; the summary works without AI.":
        "الذكاء الاصطناعي متوقف. اختر مزوداً محلياً أو عبر الإنترنت أعلاه؛ الملخص يعمل بدون ذكاء اصطناعي.",
    "AI is off. The financial summary below is calculated by Money Manager without AI; choose a local or online provider to get AI insights.":
        "الذكاء الاصطناعي متوقف. الملخص المالي أدناه يحسبه Money Manager بدون ذكاء اصطناعي؛ اختر مزوداً محلياً أو عبر الإنترنت للحصول على تحليلات الذكاء الاصطناعي.",
    "AI provider":
        "مزود الذكاء الاصطناعي",
    "AI settings saved.":
        "تم حفظ إعدادات الذكاء الاصطناعي.",
    "AI settings…":
        "إعدادات الذكاء الاصطناعي…",
    "All accounts":
        "كل الحسابات",
    "All accounts together":
        "كل الحسابات مجتمعة",
    "All amounts use one currency: currently {0} (the default is {1}). It can be changed until the first account is created. Money Manager never converts between currencies and uses no exchange rates.":
        "كل المبالغ تستخدم عملة واحدة: حالياً {0} (الافتراضية {1}). يمكن تغييرها حتى إنشاء أول حساب. Money Manager لا يحوّل أبداً بين العملات ولا يستخدم أسعار صرف.",
    "All categories":
        "كل الفئات",
    "All data was deleted.":
        "تم حذف كل البيانات.",
    "All files":
        "كل الملفات",
    "All subscriptions":
        "كل الاشتراكات",
    "All time":
        "كل الفترات",
    "all time":
        "كل الفترات",
    "All types":
        "كل الأنواع",
    "Allocated":
        "مخصص",
    "Allocation":
        "المخصص",
    "Allocation archived":
        "تمت أرشفة المخصص",
    "Allocation created":
        "تم إنشاء المخصص",
    "Allocation renamed":
        "تمت إعادة تسمية المخصص",
    "Allocation restored":
        "تمت استعادة المخصص",
    "Allocation {0!r} does not exist.":
        "المخصص {0!r} غير موجود.",
    "Allocations":
        "المخصصات",
    "Allocations exceed the real balance by {0}; move money from an allocation back to Available.":
        "المخصصات تتجاوز الرصيد الفعلي بـ {0}؛ أعد المال من أحد المخصصات إلى المتاح.",
    "Allocations organise the money you already have: set some aside for bills, a holiday or an emergency fund. It stays in your accounts, but is no longer counted as Available to spend. Goals keep their money in allocations too.":
        "المخصصات تنظم المال الذي تملكه بالفعل: ضع جزءاً جانباً للفواتير أو العطلة أو صندوق الطوارئ. يبقى في حساباتك، لكنه لم يعد يُحسب ضمن المتاح للإنفاق. الأهداف تحتفظ بمالها في مخصصات أيضاً.",
    "Already recorded":
        "مسجلة سابقاً",
    "Also remove the saved Anthropic API key":
        "احذف أيضاً مفتاح API المحفوظ من Anthropic",
    "Amount":
        "المبلغ",
    "Amount ({0})":
        "المبلغ ({0})",
    "Amount can have at most {0} decimal places.":
        "يمكن أن يحتوي المبلغ على {0} أرقام عشرية كحد أقصى.",
    "Amount column":
        "عمود المبلغ",
    "Amount must be a finite number.":
        "يجب أن يكون المبلغ عدداً محدوداً.",
    "Amount must be a number.":
        "يجب أن يكون المبلغ عدداً.",
    "Amount must be greater than zero{0}.":
        "يجب أن يكون المبلغ أكبر من الصفر{0}.",
    "Amount must not exceed {0:,} in size.":
        "يجب ألا يتجاوز المبلغ {0:,}.",
    "Amount paid ({0})":
        "المبلغ المدفوع ({0})",
    "Amount saved so far":
        "المبلغ المدخر حتى الآن",
    "Amounts":
        "المبالغ",
    "Amounts must not be floats; use a Decimal or a string such as '12.50'.":
        "يجب ألا تكون المبالغ أعداداً عشرية عائمة؛ استخدم Decimal أو نصاً مثل «12.50».",
    "An account is where your money is kept, such as a bank account or cash. Enter its balance on the day you start tracking; earlier activity is already included in that balance.":
        "الحساب هو المكان الذي يُحفظ فيه مالك، مثل حساب بنكي أو النقود. أدخل رصيده في يوم بدء المتابعة؛ النشاط السابق مضمَّن في ذلك الرصيد.",
    "An account is where your money is kept: a bank account, your cash wallet or a card. Add the first one with the balance it has today.":
        "الحساب هو المكان الذي يُحفظ فيه مالك: حساب بنكي أو محفظة نقودك أو بطاقة. أضف الأول برصيده اليوم.",
    "An account named '{0}' already exists.":
        "يوجد حساب باسم «{0}» مسبقاً.",
    "An allocation named '{0}' already exists.":
        "يوجد مخصص باسم «{0}» مسبقاً.",
    "An allocation sets money aside for a purpose, such as bills or a holiday. The money stays in your accounts; it is only no longer Available to spend.":
        "المخصص يضع المال جانباً لغرض ما، مثل الفواتير أو العطلة. يبقى المال في حساباتك؛ فقط لم يعد متاحاً للإنفاق.",
    "An investment named '{0}' already exists.":
        "يوجد استثمار باسم «{0}» مسبقاً.",
    "An unexpected error occurred. Your data has not been sent anywhere; technical details were written to the log file.":
        "حدث خطأ غير متوقع. لم تُرسَل بياناتك إلى أي مكان؛ تمت كتابة التفاصيل التقنية في ملف السجل.",
    "an unknown date":
        "تاريخ غير معروف",
    "An {0} category named '{1}' already exists.":
        "توجد فئة {0} باسم «{1}» مسبقاً.",
    "Analyse":
        "تحليل",
    "Analyse with your local model":
        "التحليل بنموذجك المحلي",
    "Animations":
        "الحركات",
    "Anthropic could not process the request: {0}":
        "تعذّر على Anthropic معالجة الطلب: {0}",
    "Anthropic did not answer within {0} seconds.":
        "لم تُجب Anthropic خلال {0} ثانية.",
    "Anthropic had a problem (HTTP {0}). Try again later.":
        "واجهت Anthropic مشكلة (HTTP {0}). حاول مرة أخرى لاحقاً.",
    "Anthropic is receiving too many requests. Try again in a minute.":
        "تتلقى Anthropic طلبات كثيرة جداً. حاول مرة أخرى بعد دقيقة.",
    "Anthropic rejected the API key. Check it in Settings.":
        "رفضت Anthropic مفتاح API. تحقق منه في الإعدادات.",
    "API key":
        "مفتاح API",
    "API key saved in {0}.":
        "تم حفظ مفتاح API في {0}.",
    "API keys are sensitive: anyone who has your key can use your Anthropic account at your cost. Money Manager keeps it in the Windows Credential Manager, never in the database, backups or logs. If you think it was exposed, remove it here and revoke it in the Anthropic Console.":
        "مفاتيح API حساسة: من يملك مفتاحك يمكنه استخدام حسابك لدى Anthropic على نفقتك. يحفظه Money Manager في مدير بيانات الاعتماد في Windows، وليس أبداً في قاعدة البيانات أو النسخ الاحتياطية أو السجلات. إن كنت تظن أنه انكشف، فاحذفه هنا وألغِه في لوحة تحكم Anthropic.",
    "API keys cannot be serialised.":
        "لا يمكن تسلسل مفاتيح API.",
    "App lock":
        "القفل",
    "Appearance":
        "المظهر",
    "Apr":
        "أبريل",
    "Archive":
        "أرشفة",
    "Archive allocation":
        "أرشفة المخصص",
    "Archive {0}?\n\nIts {1} goes back to Available. You can restore the allocation later from the Archived list.":
        "أرشفة {0}؟\n\nيعود {1} الخاص به إلى المتاح. يمكنك استعادة المخصص لاحقاً من قائمة المؤرشفة.",
    "Archived":
        "المؤرشفة",
    "Ask":
        "اسأل",
    "Ask about your finances, e.g. Why did my spending rise this month?":
        "اسأل عن ماليتك، مثلاً: لماذا ارتفعت مصاريفي هذا الشهر؟",
    "Ask again for the same period with your latest data.":
        "اسأل مجدداً عن نفس الفترة بأحدث بياناتك.",
    "Ask AI":
        "اسأل الذكاء الاصطناعي",
    "Ask for Windows Hello (PIN, fingerprint or face) when Money Manager opens and after a while without use. This keeps other people who use your computer out of the app; it does not encrypt the data file.":
        "اطلب Windows Hello (رمز PIN أو البصمة أو الوجه) عند فتح Money Manager وبعد فترة دون استخدام. هذا يمنع الأشخاص الآخرين الذين يستخدمون حاسوبك من دخول التطبيق؛ لكنه لا يشفّر ملف البيانات.",
    "Ask the advisor":
        "اسأل المستشار",
    "Asking {0} ({1}) {2}…":
        "جارٍ سؤال {0} ({1}) {2}…",
    "At this pace: {0} by the end of the month":
        "بهذه الوتيرة: {0} بنهاية الشهر",
    "Attach a photo or PDF of the receipt":
        "أرفق صورة أو ملف PDF للإيصال",
    "Attach a receipt":
        "إرفاق إيصال",
    "Attach…":
        "إرفاق…",
    "Aug":
        "غشت",
    "Automatic (local when available, otherwise online)":
        "تلقائي (محلي عند توفره، وإلا عبر الإنترنت)",
    "Automatic AI uses the local model when it is available. If it falls back to online AI, each request still needs your confirmation.":
        "الذكاء الاصطناعي التلقائي يستخدم النموذج المحلي عند توفره. وإذا انتقل إلى الإنترنت، يحتاج كل طلب إلى تأكيدك.",
    "Automatic uses the local model when Ollama is running with it, and otherwise the online provider. Online requests still show what would be sent and wait for your confirmation.":
        "الوضع التلقائي يستخدم النموذج المحلي عندما يعمل Ollama به، وإلا المزود عبر الإنترنت. الطلبات عبر الإنترنت تعرض دائماً ما سيُرسَل وتنتظر تأكيدك.",
    "Automatic: uses {0}; otherwise the online provider ({1}) at {2}. Processing stays on this computer with the local model; online requests show what would be sent and wait for your confirmation.":
        "تلقائي: يستخدم {0}؛ وإلا المزود عبر الإنترنت ({1}) على {2}. مع النموذج المحلي تبقى المعالجة على هذا الحاسوب؛ الطلبات عبر الإنترنت تعرض ما سيُرسَل وتنتظر تأكيدك.",
    "Available":
        "المتاح",
    "Available (not allocated)":
        "المتاح (غير مخصص)",
    "Available balance":
        "الرصيد المتاح",
    "Average {0} per day":
        "بمعدل {0} يومياً",
    "Backs the goal {0}":
        "يموّل الهدف {0}",
    "backup":
        "النسخة الاحتياطية",
    "Backup saved and verified{0}: {1} records in {2}.":
        "تم حفظ النسخة الاحتياطية والتحقق منها{0}: {1} سجلاً في {2}.",
    "Backups and CSV exports contain your data unencrypted. The AI insight history is stored locally and included in backups; clear it on the AI Advisor page.":
        "النسخ الاحتياطية وصادرات CSV تحتوي على بياناتك دون تشفير. سجل تحليلات الذكاء الاصطناعي محفوظ محلياً ومضمَّن في النسخ الاحتياطية؛ امسحه من صفحة المستشار الذكي.",
    "Backups without a password and CSV exports contain your financial data unencrypted. Store them somewhere safe.":
        "النسخ الاحتياطية دون كلمة مرور وصادرات CSV تحتوي على بياناتك المالية دون تشفير. احفظها في مكان آمن.",
    "Balance":
        "الرصيد",
    "Balance adjustments always affect Available money and cannot use an allocation.":
        "تسويات الرصيد تؤثر دائماً على المال المتاح ولا يمكنها استخدام مخصص.",
    "Balance adjustments do not use a category.":
        "تسويات الرصيد لا تستخدم فئة.",
    "Balance after":
        "الرصيد بعدها",
    "Balance already correct":
        "الرصيد صحيح بالفعل",
    "Balance and net worth on {0}":
        "الرصيد وصافي الثروة في {0}",
    "Balance corrected":
        "تم تصحيح الرصيد",
    "Balance correction":
        "تصحيح الرصيد",
    "Balance history":
        "تاريخ الرصيد",
    "Balance now {0}":
        "الرصيد الآن {0}",
    "Balance of your accounts":
        "رصيد حساباتك",
    "Balance on the start date ({0})":
        "الرصيد في تاريخ البدء ({0})",
    "Balance on {0}: {1}.":
        "الرصيد في {0}: {1}.",
    "Balance plus investment values at the end of each month":
        "الرصيد مضافاً إليه قيمة الاستثمارات في نهاية كل شهر",
    "Balance trend":
        "اتجاه الرصيد",
    "Balance {0} + investments":
        "الرصيد {0} + الاستثمارات",
    "Balance ÷ average monthly spending (last 3 full months)":
        "الرصيد ÷ متوسط المصاريف الشهرية (آخر 3 أشهر كاملة)",
    "Bank statements":
        "كشوف الحساب البنكية",
    "Based on your scheduled entries, subscriptions and loans only (no complete month of history yet).":
        "مبنية فقط على عملياتك المتكررة واشتراكاتك وقروضك (لا يوجد بعد شهر كامل من السجل).",
    "Before a reset":
        "قبل إعادة الضبط",
    "Before importing a backup":
        "قبل استيراد نسخة احتياطية",
    "Before restoring a safety copy":
        "قبل استعادة نسخة أمان",
    "Behind or overdue":
        "متأخرة أو فات موعدها",
    "Best month: <b>{0}</b> ({1} kept). Hardest month: <b>{2}</b> ({3}).":
        "أفضل شهر: <b>{0}</b> (احتُفظ بـ {1}). أصعب شهر: <b>{2}</b> ({3}).",
    "Borrowed":
        "مقترض",
    "Budget near its limit":
        "الميزانية قريبة من حدها",
    "Budget over the limit":
        "الميزانية تجاوزت الحد",
    "Budget removed":
        "تم حذف الميزانية",
    "Budget saved":
        "تم حفظ الميزانية",
    "Budget updated":
        "تم تعديل الميزانية",
    "Budgets":
        "الميزانيات",
    "Budgets are for expense categories.":
        "الميزانيات خاصة بفئات المصاريف.",
    "Calculated by Money Manager's fixed rules — available with or without AI.":
        "محسوب بقواعد Money Manager الثابتة — متاح مع الذكاء الاصطناعي أو بدونه.",
    "Calendar months in the range":
        "الأشهر التقويمية في الفترة",
    "Canadian dollar":
        "دولار كندي",
    "Cancelled. Nothing was sent.":
        "تم الإلغاء. لم يُرسَل شيء.",
    "Cannot be longer than {0} characters.":
        "لا يمكن أن يتجاوز {0} حرفاً.",
    "cannot be read":
        "غير مقروءة",
    "Cannot combine {0} and {1} amounts.":
        "لا يمكن الجمع بين مبالغ بـ {0} و {1}.",
    "Cannot create the folder '{0}': {1}":
        "تعذّر إنشاء المجلد «{0}»: {1}",
    "Cannot read the configuration file '{0}': {1}":
        "تعذّرت قراءة ملف الإعداد «{0}»: {1}",
    "categories over budget":
        "فئات تجاوزت الميزانية",
    "Category":
        "الفئة",
    "Category breakdowns, balance trends and month-over-month comparisons will appear here.":
        "ستظهر هنا تفاصيل الفئات واتجاهات الرصيد والمقارنات الشهرية.",
    "Category changes":
        "تغيّرات الفئات",
    "Category name:":
        "اسم الفئة:",
    "category over budget":
        "فئة تجاوزت الميزانية",
    "Category rules":
        "قواعد الفئات",
    "Category {0!r} does not exist.":
        "الفئة {0!r} غير موجودة.",
    "Category:":
        "الفئة:",
    "Change":
        "التغيّر",
    "Change budget":
        "تعديل الميزانية",
    "Changes compare with {0} – {1}":
        "المقارنة مع {0} – {1}",
    "Chart":
        "رسم بياني",
    "Charts are on the way":
        "الرسوم البيانية قادمة",
    "Check for a newer version once a day":
        "البحث عن إصدار أحدث مرة في اليوم",
    "Check now":
        "تحقق الآن",
    "Checking…":
        "جارٍ التحقق…",
    "Checks the provider without sending any financial data.":
        "يتحقق من المزود دون إرسال أي بيانات مالية.",
    "Choose a category for spending and for income (or create one with New…). You can change categories of single entries later.":
        "اختر فئة للمصاريف وأخرى للمداخيل (أو أنشئ واحدة عبر جديد…). يمكنك تغيير فئة أي عملية لاحقاً.",
    "Choose a category, or create one with New….":
        "اختر فئة، أو أنشئ واحدة عبر جديد….",
    "Choose a category.":
        "اختر فئة.",
    "Choose a date range.":
        "اختر فترة.",
    "Choose a file.":
        "اختر ملفاً.",
    "Choose a local model in Settings first.":
        "اختر أولاً نموذجاً محلياً في الإعدادات.",
    "Choose a local model in the settings first.":
        "اختر أولاً نموذجاً محلياً في الإعدادات.",
    "Choose a local or an online AI provider for insights. Your financial data is never sent online without your explicit confirmation.":
        "اختر مزود ذكاء اصطناعي محلياً أو عبر الإنترنت للتحليلات. لا تُرسَل بياناتك المالية عبر الإنترنت أبداً دون تأكيدك الصريح.",
    "Choose a month between your first account and today.":
        "اختر شهراً بين أول حساب لك واليوم.",
    "Choose a password (at least {0} characters):":
        "اختر كلمة مرور ({0} أحرف على الأقل):",
    "Choose a period of at most ten years.":
        "اختر فترة لا تتجاوز عشر سنوات.",
    "Choose a period.":
        "اختر فترة.",
    "Choose a photo (JPG, PNG, WebP, GIF, BMP) or a PDF.":
        "اختر صورة (JPG أو PNG أو WebP أو GIF أو BMP) أو ملف PDF.",
    "Choose a range of at most ten years.":
        "اختر فترة لا تتجاوز عشر سنوات.",
    "Choose a year between your first account and today.":
        "اختر سنة بين أول حساب لك واليوم.",
    "Choose active or paused.":
        "اختر نشط أو متوقف.",
    "Choose an account if the money went out of it (or came into it): it is recorded as a balance adjustment, never as income or spending. Loans count in your net worth.":
        "اختر حساباً إذا خرج المال منه (أو دخل إليه): يُسجَّل كتسوية للرصيد، وليس أبداً كدخل أو مصروف. القروض تُحسب في صافي ثروتك.",
    "Choose an account.":
        "اختر حساباً.",
    "Choose an allocation.":
        "اختر مخصصاً.",
    "Choose an allocation; moving money from Available to Available does nothing.":
        "اختر مخصصاً؛ نقل المال من المتاح إلى المتاح لا يغير شيئاً.",
    "Choose archived or active.":
        "اختر مؤرشف أو نشط.",
    "Choose dark, light or the Windows setting.":
        "اختر داكن أو فاتح أو إعداد Windows.",
    "Choose how AI features should work.":
        "اختر طريقة عمل ميزات الذكاء الاصطناعي.",
    "Choose how often it repeats.":
        "اختر وتيرة التكرار.",
    "Choose income or expense.":
        "اختر دخل أو مصروف.",
    "Choose off, local, online or automatic.":
        "اختر متوقف أو محلي أو عبر الإنترنت أو تلقائي.",
    "Choose one of the installed models.":
        "اختر أحد النماذج المثبتة.",
    "Choose one of the offered languages.":
        "اختر إحدى اللغات المقترحة.",
    "Choose one of the offered lock times.":
        "اختر إحدى مدد القفل المقترحة.",
    "Choose one of the safety copies listed.":
        "اختر إحدى نسخ الأمان المعروضة.",
    "Choose one of the supported currencies.":
        "اختر إحدى العملات المدعومة.",
    "Choose the account and check the columns. Lines already recorded in the account are skipped, so importing the same statement twice adds nothing.":
        "اختر الحساب وتحقق من الأعمدة. يتم تخطي الأسطر المسجلة سابقاً في الحساب، لذلك لا يضيف استيراد الكشف نفسه مرتين شيئاً.",
    "Choose the account the payment was made from.":
        "اختر الحساب الذي تمت منه الدفعة.",
    "Choose the investment category for the expense.":
        "اختر فئة الاستثمار للمصروف.",
    "Choose two different accounts.":
        "اختر حسابين مختلفين.",
    "Choose what the advisor should do.":
        "اختر ما يجب أن يفعله المستشار.",
    "Choose when paying":
        "اختر عند الدفع",
    "Choose whether you lent or borrowed the money.":
        "حدد هل أقرضت المال أم اقترضته.",
    "Choose which local model to use.":
        "اختر النموذج المحلي الذي ستستخدمه.",
    "Choose yes or no.":
        "اختر نعم أو لا.",
    "Claude model":
        "نموذج Claude",
    "Clear filters":
        "مسح عوامل التصفية",
    "Clear history":
        "مسح السجل",
    "Clear insight history":
        "مسح سجل التحليلات",
    "Column {0}":
        "العمود {0}",
    "Compared with this category's spending in the current calendar month.":
        "مقارنة بمصاريف هذه الفئة في الشهر الحالي.",
    "Configuration file":
        "ملف الإعداد",
    "Configured: {0} at {1} (not contacted).":
        "مُعَدّ: {0} على {1} (لم يتم الاتصال).",
    "Confirm each payment when it happens: Record creates the expense, Skip moves on without one.":
        "أكّد كل دفعة عند حدوثها: تسجيل ينشئ المصروف، وتخطٍّ يتابع دون مصروف.",
    "Confirm it's you with Windows Hello — your PIN, fingerprint or face.":
        "أكّد هويتك عبر Windows Hello — رمز PIN أو البصمة أو الوجه.",
    "Confirm the earlier payment of this subscription first.":
        "أكّد أولاً الدفعة السابقة لهذا الاشتراك.",
    "Confirm with Windows Hello…":
        "أكّد عبر Windows Hello…",
    "Confirms the payment due {0} by recording one expense. The next payment will then be due {1}.":
        "يؤكد الدفعة المستحقة في {0} بتسجيل مصروف واحد. ستكون الدفعة التالية مستحقة في {1}.",
    "Connected: {0} at {1}.":
        "متصل: {0} على {1}.",
    "Consent is only given by accepting a DataDisclosure.":
        "لا تُمنح الموافقة إلا بقبول إفصاح البيانات (DataDisclosure).",
    "Contributed {0} · withdrawn {1}":
        "مساهمات {0} · مسحوبات {1}",
    "Contribution":
        "مساهمة",
    "contribution":
        "المساهمة",
    "Contributions & withdrawals":
        "المساهمات والمسحوبات",
    "Correct balance":
        "تصحيح الرصيد",
    "Correct balance…":
        "تصحيح الرصيد…",
    "Correct the balance of {0}":
        "تصحيح رصيد {0}",
    "Could not archive the allocation":
        "تعذّرت أرشفة المخصص",
    "Could not compute statistics":
        "تعذّر حساب الإحصائيات",
    "Could not compute the summary":
        "تعذّر حساب الملخص",
    "Could not create category":
        "تعذّر إنشاء الفئة",
    "Could not delete goal":
        "تعذّر حذف الهدف",
    "Could not delete the account":
        "تعذّر حذف الحساب",
    "Could not delete the loan":
        "تعذّر حذف القرض",
    "Could not delete the transfer":
        "تعذّر حذف التحويل",
    "Could not delete transaction":
        "تعذّر حذف العملية",
    "Could not list the safety copies: {0}":
        "تعذّر عرض نسخ الأمان: {0}",
    "Could not load accounts":
        "تعذّر تحميل الحسابات",
    "Could not load allocations":
        "تعذّر تحميل المخصصات",
    "Could not load budgets":
        "تعذّر تحميل الميزانيات",
    "Could not load goals":
        "تعذّر تحميل الأهداف",
    "Could not load investments":
        "تعذّر تحميل الاستثمارات",
    "Could not load subscriptions":
        "تعذّر تحميل الاشتراكات",
    "Could not load the dashboard":
        "تعذّر تحميل لوحة القيادة",
    "Could not load transactions":
        "تعذّر تحميل العمليات",
    "Could not prepare the report":
        "تعذّر تحضير التقرير",
    "Could not reach the update server. Are you online?":
        "تعذّر الوصول إلى خادم التحديثات. هل أنت متصل بالإنترنت؟",
    "Could not reach {0}. Check the internet connection.":
        "تعذّر الوصول إلى {0}. تحقق من الاتصال بالإنترنت.",
    "Could not read from the Windows Credential Manager.":
        "تعذّرت القراءة من مدير بيانات الاعتماد في Windows.",
    "Could not read the file: {0}":
        "تعذّرت قراءة الملف: {0}",
    "Could not read the statement":
        "تعذّرت قراءة الكشف",
    "Could not remove the budget":
        "تعذّر حذف الميزانية",
    "Could not remove the key from the Windows Credential Manager.":
        "تعذّر حذف المفتاح من مدير بيانات الاعتماد في Windows.",
    "Could not remove the repayment":
        "تعذّر حذف السداد",
    "Could not rename the allocation":
        "تعذّرت إعادة تسمية المخصص",
    "Could not restore the allocation":
        "تعذّرت استعادة المخصص",
    "Could not save the report":
        "تعذّر حفظ التقرير",
    "Could not save the setting":
        "تعذّر حفظ الإعداد",
    "Could not save to the Windows Credential Manager.":
        "تعذّر الحفظ في مدير بيانات الاعتماد في Windows.",
    "Could not undo the move":
        "تعذّر التراجع عن النقل",
    "Could not update the investment":
        "تعذّر تعديل الاستثمار",
    "Could not update the subscription":
        "تعذّر تعديل الاشتراك",
    "Could not write the file: {0}":
        "تعذّرت كتابة الملف: {0}",
    "Create a budget":
        "إنشاء ميزانية",
    "Create a category first.":
        "أنشئ فئة أولاً.",
    "Create a goal such as an emergency fund, a trip or a new laptop. Keep its money in an allocation and track your progress towards the target.":
        "أنشئ هدفاً مثل صندوق طوارئ أو رحلة أو حاسوب جديد. احتفظ بماله في مخصص وتابع تقدمك نحو المبلغ المستهدف.",
    "Create account":
        "إنشاء الحساب",
    "Create allocation":
        "إنشاء المخصص",
    "Create an account first":
        "أنشئ حساباً أولاً",
    "Create an account first.":
        "أنشئ حساباً أولاً.",
    "Create an account first; the report covers its months.":
        "أنشئ حساباً أولاً؛ التقرير يغطي أشهره.",
    "Create an account first; the report covers its years.":
        "أنشئ حساباً أولاً؛ التقرير يغطي سنواته.",
    "Create an account to get started":
        "أنشئ حساباً للبدء",
    "Create an allocation":
        "إنشاء مخصص",
    "Create goal":
        "إنشاء الهدف",
    "Create savings targets with deadlines and follow your progress.":
        "أنشئ أهدافاً للادخار بمواعيد نهائية وتابع تقدمك.",
    "Credit column (money in)":
        "عمود الدائن (المال الداخل)",
    "Crypto":
        "عملات مشفرة",
    "Currency":
        "العملة",
    "Currency and appearance options will be added here.":
        "ستُضاف هنا خيارات العملة والمظهر.",
    "Currency must be a three-letter ISO 4217 code such as 'MAD'.":
        "يجب أن تكون العملة رمزاً من ثلاثة أحرف وفق ISO 4217 مثل «MAD».",
    "Currency set to {0}.":
        "تم تعيين العملة إلى {0}.",
    "Current value":
        "القيمة الحالية",
    "Current value ({0})":
        "القيمة الحالية ({0})",
    "Custom":
        "مخصصة",
    "Custom range…":
        "فترة مخصصة…",
    "Daily automatic copy":
        "نسخة يومية تلقائية",
    "Daily copies":
        "النسخ اليومية",
    "Dark":
        "داكن",
    "Dashboard":
        "لوحة القيادة",
    "Data folder":
        "مجلد البيانات",
    "Data schema":
        "مخطط البيانات",
    "Database created":
        "تاريخ إنشاء قاعدة البيانات",
    "Database file":
        "ملف قاعدة البيانات",
    "Date":
        "التاريخ",
    "Date cannot be before the account's opening date ({0}); the opening balance already includes earlier activity.":
        "لا يمكن أن يسبق التاريخ تاريخ فتح الحساب ({0})؛ الرصيد الافتتاحي يشمل النشاط السابق.",
    "Date cannot be before {0}.":
        "لا يمكن أن يسبق التاريخ {0}.",
    "Date cannot be in the future.":
        "لا يمكن أن يكون التاريخ في المستقبل.",
    "Date column":
        "عمود التاريخ",
    "Date format":
        "صيغة التاريخ",
    "day":
        "يوم",
    "days":
        "أيام",
    "Deadline":
        "الموعد النهائي",
    "Debit column (money out)":
        "عمود المدين (المال الخارج)",
    "Debt {0!r} does not exist.":
        "الدين {0!r} غير موجود.",
    "Dec":
        "دجنبر",
    "Decrease":
        "إنقاص",
    "Delete":
        "حذف",
    "Delete account":
        "حذف الحساب",
    "Delete all data":
        "حذف كل البيانات",
    "Delete all of your data?":
        "حذف كل بياناتك؟",
    "Delete entry":
        "حذف القيد",
    "Delete every stored AI answer? Your financial data is not affected.":
        "حذف كل إجابات الذكاء الاصطناعي المحفوظة؟ لا تتأثر بياناتك المالية.",
    "Delete goal":
        "حذف الهدف",
    "Delete investment":
        "حذف الاستثمار",
    "Delete loan":
        "حذف القرض",
    "Delete recurring entry":
        "حذف العملية المتكررة",
    "Delete selected":
        "حذف المحدد",
    "Delete subscription":
        "حذف الاشتراك",
    "Delete the account {0}?\n\nOnly an account without any transactions can be deleted. This cannot be undone.":
        "حذف الحساب {0}؟\n\nلا يمكن حذف إلا حساب بلا أي عملية. لا يمكن التراجع عن ذلك.",
    "Delete the goal “{0}”? Its money stays in your balance either way.":
        "حذف الهدف «{0}»؟ يبقى ماله في رصيدك في كل الأحوال.",
    "Delete the goal “{0}”? This cannot be undone.":
        "حذف الهدف «{0}»؟ لا يمكن التراجع عن ذلك.",
    "Delete the subscription “{0}”? Expenses already recorded for it stay in your transactions.":
        "حذف الاشتراك «{0}»؟ تبقى المصاريف المسجلة له في عملياتك.",
    "Delete this transaction?\n\n{0} · {1} · {2}\n\nYour balance will be recalculated. This cannot be undone.":
        "حذف هذه العملية؟\n\n{0} · {1} · {2}\n\nسيُعاد حساب رصيدك. لا يمكن التراجع عن ذلك.",
    "Delete this transfer?\n\n{0} · {1} · {2}\n\nBoth sides are removed and both balances are recalculated. This cannot be undone.":
        "حذف هذا التحويل؟\n\n{0} · {1} · {2}\n\nيُحذف الطرفان ويُعاد حساب الرصيدين. لا يمكن التراجع عن ذلك.",
    "Delete this value?":
        "حذف هذه القيمة؟",
    "Delete this {0}?{1}":
        "حذف هذه {0}؟{1}",
    "Delete transaction":
        "حذف العملية",
    "Delete transfer":
        "حذف التحويل",
    "Delete value":
        "حذف القيمة",
    "Delete “{0}” and its history? Expenses already recorded for its contributions stay in your transactions.":
        "حذف «{0}» وسجله؟ تبقى المصاريف المسجلة لمساهماته في عملياتك.",
    "Delete “{0}” and its repayments? Money already moved through your accounts stays recorded.":
        "حذف «{0}» ودفعات سداده؟ يبقى المال الذي مرّ عبر حساباتك مسجلاً.",
    "Deletes every account, transaction, allocation, goal, subscription, investment, setting and AI insight. A safety backup of the database is written first. This cannot be undone from inside the app.":
        "يحذف كل الحسابات والعمليات والمخصصات والأهداف والاشتراكات والاستثمارات والإعدادات وتحليلات الذكاء الاصطناعي. تُكتب أولاً نسخة أمان من قاعدة البيانات. لا يمكن التراجع عن ذلك من داخل التطبيق.",
    "Deleting a contribution paid from your accounts also deletes its expense.":
        "حذف مساهمة مدفوعة من حساباتك يحذف مصروفها أيضاً.",
    "Description":
        "الوصف",
    "Description column":
        "عمود الوصف",
    "Destination: {0} ({1}) · model {2}":
        "الوجهة: {0} ({1}) · النموذج {2}",
    "Download…":
        "تنزيل…",
    "Due by":
        "يُسدَّد قبل",
    "Due in the next {0} days":
        "مستحقة خلال الأيام الـ {0} القادمة",
    "Due today":
        "مستحقة اليوم",
    "due today":
        "مستحقة اليوم",
    "due tomorrow":
        "مستحقة غداً",
    "Due {0}":
        "الموعد {0}",
    "Duplicate navigation key: {0!r}":
        "مفتاح تنقل مكرر: {0!r}",
    "e.g. Bank account":
        "مثلاً: حساب بنكي",
    "e.g. Bills, Holiday, Emergency fund":
        "مثلاً: الفواتير، العطلة، صندوق الطوارئ",
    "e.g. Emergency Fund":
        "مثلاً: صندوق الطوارئ",
    "e.g. Groceries at Marjane":
        "مثلاً: مشتريات من مرجان",
    "e.g. llama3.2":
        "مثلاً: llama3.2",
    "e.g. MSCI World ETF":
        "مثلاً: صندوق MSCI World",
    "e.g. Netflix":
        "مثلاً: Netflix",
    "e.g. Rent, Salary":
        "مثلاً: الكراء، الراتب",
    "e.g. Sami, Car loan":
        "مثلاً: سامي، قرض السيارة",
    "Edit":
        "تعديل",
    "Edit account":
        "تعديل الحساب",
    "Edit goal":
        "تعديل الهدف",
    "Edit investment":
        "تعديل الاستثمار",
    "Edit loan":
        "تعديل القرض",
    "Edit recurring entry":
        "تعديل العملية المتكررة",
    "Edit subscription":
        "تعديل الاشتراك",
    "Edit transaction":
        "تعديل العملية",
    "Edit…":
        "تعديل…",
    "Emergency runway":
        "احتياطي الطوارئ",
    "Empty":
        "فارغ",
    "Enter a keyword of 2 to 60 letters or digits.":
        "أدخل كلمة مفتاحية من 2 إلى 60 حرفاً أو رقماً.",
    "Enter a model name.":
        "أدخل اسم نموذج.",
    "Enter a valid calendar date.":
        "أدخل تاريخاً صالحاً.",
    "Enter an amount.":
        "أدخل مبلغاً.",
    "Enter an API key.":
        "أدخل مفتاح API.",
    "Enter only the scheme, host and port of the local model.":
        "أدخل فقط البروتوكول والمضيف والمنفذ للنموذج المحلي.",
    "Enter the current value to see the profit or loss.":
        "أدخل القيمة الحالية لترى الربح أو الخسارة.",
    "Enter the timeout as a whole number of seconds.":
        "أدخل المهلة كعدد صحيح من الثواني.",
    "Enter what the investment is worth, e.g. from your broker's app. A value entered for the same day replaces the earlier one.":
        "أدخل قيمة الاستثمار، مثلاً من تطبيق الوسيط. القيمة المدخلة لنفس اليوم تحل محل السابقة.",
    "Entry added":
        "تمت إضافة العملية",
    "Entry deleted":
        "تم حذف العملية",
    "Entry updated":
        "تم تعديل العملية",
    "Entry updated · rule learned":
        "تم تعديل العملية · تم تعلم قاعدة",
    "Entry {0!r} does not exist.":
        "القيد {0!r} غير موجود.",
    "Euro":
        "يورو",
    "Every":
        "كل",
    "Every 3 months":
        "كل 3 أشهر",
    "Every 3 months, day {0}":
        "كل 3 أشهر، يوم {0}",
    "Every month":
        "كل شهر",
    "Every week":
        "كل أسبوع",
    "Every year":
        "كل سنة",
    "Everything is on schedule":
        "كل شيء في موعده",
    "Everything within its limit":
        "كل شيء ضمن حدوده",
    "Exactly what will be sent:":
        "بالضبط ما سيُرسَل:",
    "Expense":
        "مصروف",
    "expense":
        "المصاريف",
    "Expenses":
        "المصاريف",
    "Expenses in view":
        "المصاريف المعروضة",
    "Expenses this month":
        "مصاريف هذا الشهر",
    "Expenses · {0}":
        "المصاريف · {0}",
    "Export and import":
        "التصدير والاستيراد",
    "Export backup":
        "تصدير نسخة احتياطية",
    "Export backup…":
        "تصدير نسخة احتياطية…",
    "Export transactions":
        "تصدير العمليات",
    "Export transactions (CSV)…":
        "تصدير العمليات (CSV)…",
    "External (not from your accounts)":
        "خارجي (ليس من حساباتك)",
    "External money (e.g. invested before you started tracking): your balance does not change.":
        "مال خارجي (مثلاً استُثمر قبل بدء المتابعة): رصيدك لا يتغير.",
    "falling":
        "منخفضة",
    "Feb":
        "فبراير",
    "Filter by {0}":
        "تصفية حسب {0}",
    "financial analysis":
        "التحليل المالي",
    "Financial health":
        "الصحة المالية",
    "Financial information about you will be sent over the internet to {0} ({1}) to generate the answer. It leaves this computer and is handled under {2}'s terms and data-retention policy. Money Manager sends only the summary shown below, never your database.":
        "سيتم إرسال معلومات مالية عنك عبر الإنترنت إلى {0} ({1}) لإنتاج الإجابة. تغادر هذا الحاسوب وتُعالَج وفق شروط {2} وسياسة الاحتفاظ بالبيانات لديها. يرسل Money Manager فقط الملخص المعروض أدناه، وليس قاعدة بياناتك أبداً.",
    "Financial summary":
        "الملخص المالي",
    "Find installed models":
        "البحث عن النماذج المثبتة",
    "First date":
        "التاريخ الأول",
    "Follow your contributions and holdings. Values are entered by you; no market data is fetched and no advice is given.":
        "تابع مساهماتك وأصولك. القيم تُدخلها أنت؛ لا يتم جلب بيانات السوق ولا تقديم أي نصيحة.",
    "Frequency":
        "التكرار",
    "Fridays":
        "أيام الجمعة",
    "From":
        "من",
    "From <b>{0}</b> at the end of {1} to <b>{2}</b> on {3} ({4}).":
        "من <b>{0}</b> في نهاية {1} إلى <b>{2}</b> في {3} ({4}).",
    "From account":
        "من الحساب",
    "From date":
        "من تاريخ",
    "From {0}":
        "من {0}",
    "fully repaid":
        "سُدِّد بالكامل",
    "Goal":
        "الهدف",
    "Goal contribution: {name}":
        "مساهمة في الهدف: {name}",
    "Goal not available":
        "الهدف غير متاح",
    "Goal withdrawal: {name}":
        "سحب من الهدف: {name}",
    "Goal {0!r} does not exist.":
        "الهدف {0!r} غير موجود.",
    "Goals":
        "الأهداف",
    "Goals below their expected pace":
        "أهداف أبطأ من الوتيرة المتوقعة",
    "Goals keep their money in one":
        "الأهداف تحتفظ بمالها في مخصص",
    "Goals on {0}":
        "الأهداف في {0}",
    "Gold":
        "ذهب",
    "Group thousands with spaces, e.g. 1 200 000.":
        "افصل الآلاف بمسافات، مثلاً 1 200 000.",
    "Holdings":
        "الأصول",
    "How your total balance is allocated":
        "كيف يتوزع رصيدك الإجمالي",
    "I borrowed money (I owe it)":
        "اقترضت مالاً (أنا مدين به)",
    "I lent money (someone owes me)":
        "أقرضت مالاً (شخص مدين لي)",
    "I understand that this information will leave my computer.":
        "أفهم أن هذه المعلومات ستغادر حاسوبي.",
    "I'll track it manually (money outside the app)":
        "سأتابعه يدوياً (مال خارج التطبيق)",
    "Import 1 entry":
        "استيراد عملية واحدة",
    "Import a bank statement (CSV file)":
        "استيراد كشف حساب بنكي (ملف CSV)",
    "Import backup":
        "استيراد نسخة احتياطية",
    "Import backup…":
        "استيراد نسخة احتياطية…",
    "Import bank statement":
        "استيراد كشف حساب بنكي",
    "Import complete":
        "اكتمل الاستيراد",
    "Import {0}":
        "استيراد {0}",
    "Import {0} entries":
        "استيراد {0} عمليات",
    "imported":
        "مستوردة",
    "Imported from a bank statement":
        "مستورد من كشف حساب بنكي",
    "Imported from {0}":
        "مستورد من {0}",
    "Import…":
        "استيراد…",
    "In 1 allocation":
        "في مخصص واحد",
    "In a new allocation for this goal (recommended)":
        "في مخصص جديد لهذا الهدف (موصى به)",
    "In an allocation I already have":
        "في مخصص لدي بالفعل",
    "In budgeted categories":
        "في الفئات ذات الميزانية",
    "in goals":
        "في الأهداف",
    "In {0} allocations":
        "في {0} مخصصات",
    "In {0} days":
        "خلال {0} أيام",
    "Included:\n":
        "مضمَّن:\n",
    "Income":
        "المداخيل",
    "income":
        "المداخيل",
    "Income and expenses recorded automatically, e.g. salary or rent":
        "مداخيل ومصاريف تُسجَّل تلقائياً، مثل الراتب أو الكراء",
    "Income and expenses that repeat — salary, rent, savings — are recorded automatically on each date. Subscriptions you confirm one by one stay on the Subscriptions page.":
        "المداخيل والمصاريف التي تتكرر — الراتب، الكراء، الادخار — تُسجَّل تلقائياً في كل تاريخ. الاشتراكات التي تؤكدها واحدة تلو الأخرى تبقى في صفحة الاشتراكات.",
    "Income goes to":
        "المداخيل تذهب إلى",
    "Income in view":
        "المداخيل المعروضة",
    "Income this month":
        "مداخيل هذا الشهر",
    "Income vs expenses":
        "المداخيل مقابل المصاريف",
    "Income · {0}":
        "المداخيل · {0}",
    "Increase":
        "زيادة",
    "Initial allocation":
        "المبلغ الأولي للمخصص",
    "Insight history":
        "سجل التحليلات",
    "Insights":
        "التحليلات",
    "Into account":
        "إلى الحساب",
    "Invalid category kind {0!r}; expected one of: {1}.":
        "نوع فئة غير صالح {0!r}؛ القيم المتوقعة: {1}.",
    "Invalid frequency {0!r}; expected one of: {1}.":
        "تكرار غير صالح {0!r}؛ القيم المتوقعة: {1}.",
    "Invalid investment type {0!r}; expected one of: {1}.":
        "نوع استثمار غير صالح {0!r}؛ القيم المتوقعة: {1}.",
    "Invalid reference.":
        "مرجع غير صالح.",
    "Invalid transaction type {0!r}; expected one of: {1}.":
        "نوع عملية غير صالح {0!r}؛ القيم المتوقعة: {1}.",
    "Invested":
        "المستثمر",
    "Investment categories":
        "فئات الاستثمار",
    "Investment categories…":
        "فئات الاستثمار…",
    "Investment category":
        "فئة الاستثمار",
    "Investment contribution":
        "مساهمة في استثمار",
    "Investment contributions were {0}, {1} of income.":
        "بلغت المساهمات في الاستثمار {0}، أي {1} من المداخيل.",
    "Investment rate {0} of income":
        "نسبة الاستثمار {0} من المداخيل",
    "Investment {0!r} does not exist.":
        "الاستثمار {0!r} غير موجود.",
    "Investments":
        "الاستثمارات",
    "Investments (latest values entered)":
        "الاستثمارات (آخر القيم المدخلة)",
    "Investments and loans":
        "الاستثمارات والقروض",
    "Investments excluded · top 5, the rest as Other":
        "دون الاستثمارات · أكبر 5، والباقي ضمن «أخرى»",
    "it contains no tables.":
        "لا يحتوي على أي جدول.",
    "It keeps reminding you here. Right-click the icon to quit.":
        "يواصل تذكيرك هنا. انقر بزر الفأرة الأيمن على الأيقونة للخروج.",
    "its tables do not match this version of Money Manager.":
        "جداوله لا تطابق هذا الإصدار من Money Manager.",
    "Jan":
        "يناير",
    "Jul":
        "يوليوز",
    "Jun":
        "يونيو",
    "Keep Money Manager running in the notification area when the window is closed":
        "إبقاء Money Manager يعمل في منطقة الإشعارات عند إغلاق النافذة",
    "Keep recurring payments under control.":
        "تحكم في دفعاتك المتكررة.",
    "Keep the money in “{0}”":
        "الاحتفاظ بالمال في «{0}»",
    "Key facts":
        "حقائق أساسية",
    "Keyword in the description:":
        "الكلمة المفتاحية في الوصف:",
    "Kind":
        "النوع",
    "Language":
        "اللغة",
    "Largest expenses":
        "أكبر المصاريف",
    "Largest spending category: {0}, {1} ({2} of spending).":
        "أكبر فئة مصاريف: {0}، {1} ({2} من المصاريف).",
    "Last 12 months":
        "آخر 12 شهراً",
    "Last 3 months":
        "آخر 3 أشهر",
    "Last 30 days":
        "آخر 30 يوماً",
    "Last 6 months · adjustments excluded":
        "آخر 6 أشهر · دون التسويات",
    "Last month":
        "الشهر الماضي",
    "Last paid":
        "آخر دفعة",
    "Last valued":
        "آخر تقييم",
    "Last year":
        "السنة الماضية",
    "Latest known values":
        "آخر القيم المعروفة",
    "Left":
        "المتبقي",
    "Left to repay: {0}.":
        "المتبقي للسداد: {0}.",
    "Left to spend":
        "المتبقي للإنفاق",
    "Lent":
        "مُقرَض",
    "Light":
        "فاتح",
    "Limit":
        "الحد",
    "Line":
        "السطر",
    "Loan deleted":
        "تم حذف القرض",
    "Loan from {0}":
        "قرض من {0}",
    "Loan recorded":
        "تم تسجيل القرض",
    "Loan to {0}":
        "قرض إلى {0}",
    "Loan updated":
        "تم تعديل القرض",
    "Loans":
        "القروض",
    "Loans (owed to you − you owe)":
        "القروض (ما يُدان لك − ما تدين به)",
    "Loans and debts":
        "القروض والديون",
    "Local":
        "محلي",
    "Local AI (Ollama) processes the financial summary on this computer; nothing is sent over the internet.":
        "الذكاء الاصطناعي المحلي (Ollama) يعالج الملخص المالي على هذا الحاسوب؛ لا يُرسَل شيء عبر الإنترنت.",
    "Local AI ({0} via Ollama): your financial summary is processed on this computer and is not sent over the internet.":
        "ذكاء اصطناعي محلي ({0} عبر Ollama): يُعالَج ملخصك المالي على هذا الحاسوب ولا يُرسَل عبر الإنترنت.",
    "Local data storage":
        "التخزين المحلي للبيانات",
    "Local model":
        "النموذج المحلي",
    "Local model (Ollama, on this computer)":
        "نموذج محلي (Ollama، على هذا الحاسوب)",
    "Lock Money Manager with Windows Hello":
        "قفل Money Manager عبر Windows Hello",
    "Lock now":
        "اقفل الآن",
    "Lock with Windows Hello":
        "القفل عبر Windows Hello",
    "Log files":
        "ملفات السجل",
    "Lowest point: {0} on {1}. On {2}: {3}.":
        "أدنى نقطة: {0} في {1}. في {2}: {3}.",
    "Made by Money Manager {0} on your computer from the entries you recorded. Amounts in {1}. Transfers between your accounts and balance corrections are not counted as income or spending.":
        "أنشأه Money Manager {0} على حاسوبك من العمليات التي سجلتها. المبالغ بـ {1}. التحويلات بين حساباتك وتصحيحات الرصيد لا تُحسب مداخيل ولا مصاريف.",
    "Made by Money Manager {0} on your computer from the entries you recorded. Amounts in {1}. Transfers between your accounts, loans and balance corrections are not counted as income or spending.":
        "أنشأه Money Manager {0} على حاسوبك من العمليات التي سجلتها. المبالغ بـ {1}. التحويلات بين حساباتك والقروض وتصحيحات الرصيد لا تُحسب مداخيل ولا مصاريف.",
    "Mar":
        "مارس",
    "Mark investment categories to track this":
        "حدّد فئات الاستثمار لمتابعة هذا",
    "Match the balance your bank shows (recorded as an adjustment)":
        "طابق الرصيد الذي يعرضه بنكك (يُسجَّل كتسوية)",
    "May":
        "ماي",
    "Measured from your own data by fixed rules — no AI, no judgements.":
        "مقاس من بياناتك بقواعد ثابتة — دون ذكاء اصطناعي ودون أحكام.",
    "Mondays":
        "أيام الاثنين",
    "Money / Allocations":
        "المال / المخصصات",
    "Money gets tight around {0}: the balance is projected at {1}.":
        "يصبح المال ضيقاً حوالي {0}: الرصيد المتوقع {1}.",
    "Money kept in the allocation “{0}”":
        "مال محفوظ في المخصص «{0}»",
    "Money kept in the allocation “{0}”.":
        "مال محفوظ في المخصص «{0}».",
    "Money Manager backup":
        "نسخة احتياطية من Money Manager",
    "Money Manager is locked":
        "Money Manager مقفل",
    "Money Manager is still running":
        "Money Manager لا يزال يعمل",
    "Money Manager saves a copy of all your data before every reset, import or restore, before an update changes how data is stored, and once a day. Restoring a copy replaces your current data, which is itself saved first, so a restore can be undone the same way.":
        "يحفظ Money Manager نسخة من كل بياناتك قبل كل إعادة ضبط أو استيراد أو استعادة، وقبل أن يغير تحديثٌ طريقة تخزين البيانات، ومرة في اليوم. استعادة نسخة تستبدل بياناتك الحالية، التي تُحفظ هي أيضاً أولاً، لذلك يمكن التراجع عن الاستعادة بالطريقة نفسها.",
    "Money Manager shows {0} today. Enter the balance your bank (or wallet) shows; the difference is recorded as a balance adjustment, so nothing is overwritten and you can see the correction in Transactions.":
        "يعرض Money Manager اليوم {0}. أدخل الرصيد الذي يعرضه بنكك (أو محفظتك)؛ يُسجَّل الفرق كتسوية للرصيد، فلا يُستبدَل شيء ويمكنك رؤية التصحيح في العمليات.",
    "Money Manager works fully offline. The only network connections it can make are to a local Ollama server and, when you confirm a request, to Anthropic's API.":
        "يعمل Money Manager دون اتصال بالكامل. الاتصالات الشبكية الوحيدة الممكنة هي مع خادم Ollama محلي، ومع واجهة Anthropic عند تأكيدك لطلب.",
    "Money Manager {0} is available":
        "Money Manager {0} متاح",
    "MONEY MANAGER · MONTHLY REPORT":
        "MONEY MANAGER · التقرير الشهري",
    "MONEY MANAGER · YEARLY REPORT":
        "MONEY MANAGER · التقرير السنوي",
    "Money may get tight":
        "قد يصبح المال ضيقاً",
    "Money moved":
        "تم نقل المال",
    "Money moved in or out after the last value — update the value to see the current return.":
        "دخل مال أو خرج بعد آخر قيمة — حدّث القيمة لترى العائد الحالي.",
    "Money moved through":
        "مرّ المال عبر",
    "Money organisation":
        "تنظيم المال",
    "Money that actually enters or leaves your accounts.":
        "المال الذي يدخل حساباتك أو يخرج منها فعلاً.",
    "Money you lent to someone or borrowed — a friend, a car loan. What is left counts in your net worth.":
        "مال أقرضته لشخص أو اقترضته — صديق، قرض سيارة. ما تبقى يُحسب في صافي ثروتك.",
    "Month":
        "الشهر",
    "Month by month":
        "شهراً بشهر",
    "Month-end balance":
        "رصيد نهاية الشهر",
    "Month:":
        "الشهر:",
    "Monthly":
        "شهرياً",
    "Monthly comparison":
        "المقارنة الشهرية",
    "Monthly cost":
        "الكلفة الشهرية",
    "Monthly cost by category":
        "الكلفة الشهرية حسب الفئة",
    "Monthly limit":
        "الحد الشهري",
    "Monthly limits per spending category, compared with this month so far.":
        "حدود شهرية لكل فئة مصاريف، مقارنة بهذا الشهر حتى الآن.",
    "Monthly report":
        "التقرير الشهري",
    "Monthly report…":
        "التقرير الشهري…",
    "Monthly summary":
        "ملخص الشهر",
    "Monthly, day {0}":
        "شهرياً، يوم {0}",
    "More is set aside than you have":
        "المخصص أكثر مما تملك",
    "More is set aside than you have: Available is short by {0}. Take money out of an allocation to fix it.":
        "المخصص أكثر مما تملك: ينقص المتاح بمقدار {0}. اسحب مالاً من مخصص لإصلاح ذلك.",
    "More settings coming":
        "مزيد من الإعدادات قريباً",
    "Moroccan dirham":
        "درهم مغربي",
    "Most expensive":
        "الأغلى",
    "Move":
        "نقل",
    "Move from Available now · {0} available":
        "النقل من المتاح الآن · {0} متاح",
    "Move money":
        "نقل المال",
    "Move money between two of your accounts":
        "نقل المال بين حسابين من حساباتك",
    "Move the money back to Available":
        "إعادة المال إلى المتاح",
    "Move undone":
        "تم التراجع عن النقل",
    "Moves money between your allocations and Available. Your accounts and your total balance do not change.":
        "ينقل المال بين مخصصاتك والمتاح. حساباتك ورصيدك الإجمالي لا يتغيران.",
    "Moves money between your own accounts. Your total stays the same, and a transfer never counts as income or spending.":
        "ينقل المال بين حساباتك الخاصة. يبقى مجموعك كما هو، والتحويل لا يُحسب أبداً كدخل أو مصروف.",
    "Moves money from Available ({0}) into the allocation “{1}”. Your total balance does not change.":
        "ينقل المال من المتاح ({0}) إلى المخصص «{1}». رصيدك الإجمالي لا يتغير.",
    "Moves money from the allocation “{0}” ({1}) back to Available. Your total balance does not change.":
        "ينقل المال من المخصص «{0}» ({1}) إلى المتاح. رصيدك الإجمالي لا يتغير.",
    "Moving money into an allocation never changes your total balance.":
        "نقل المال إلى مخصص لا يغير رصيدك الإجمالي أبداً.",
    "Must be text.":
        "يجب أن يكون نصاً.",
    "Name":
        "الاسم",
    "Name cannot be empty.":
        "لا يمكن أن يكون الاسم فارغاً.",
    "Name cannot be longer than {0} characters.":
        "لا يمكن أن يتجاوز الاسم {0} حرفاً.",
    "Name must be text.":
        "يجب أن يكون الاسم نصاً.",
    "Near limit":
        "قريب من الحد",
    "Needed per month":
        "المطلوب شهرياً",
    "negative balance adjustment":
        "تسوية سالبة للرصيد",
    "Net":
        "الصافي",
    "Net change":
        "التغير الصافي",
    "Net invested":
        "صافي المستثمر",
    "Net worth":
        "صافي الثروة",
    "Never sent:\n":
        "لا يُرسَل أبداً:\n",
    "New":
        "جديدة",
    "New account":
        "حساب جديد",
    "New account (Ctrl+N)":
        "حساب جديد (Ctrl+N)",
    "New allocation":
        "مخصص جديد",
    "New allocation (Ctrl+N)":
        "مخصص جديد (Ctrl+N)",
    "New budget":
        "ميزانية جديدة",
    "New budget (Ctrl+N)":
        "ميزانية جديدة (Ctrl+N)",
    "New entry":
        "عملية جديدة",
    "New expense category":
        "فئة مصاريف جديدة",
    "New goal":
        "هدف جديد",
    "New goal (Ctrl+N)":
        "هدف جديد (Ctrl+N)",
    "New investment":
        "استثمار جديد",
    "New investment (Ctrl+N)":
        "استثمار جديد (Ctrl+N)",
    "New investment category":
        "فئة استثمار جديدة",
    "New loan":
        "قرض جديد",
    "New loan…":
        "قرض جديد…",
    "New name:":
        "الاسم الجديد:",
    "New recurring entry":
        "عملية متكررة جديدة",
    "New subscription":
        "اشتراك جديد",
    "New subscription (Ctrl+N)":
        "اشتراك جديد (Ctrl+N)",
    "New {0} category":
        "فئة {0} جديدة",
    "New…":
        "جديد…",
    "Next 6 months · scheduled entries, subscriptions, loans and your usual spending":
        "الأشهر الستة القادمة · العمليات المتكررة والاشتراكات والقروض ومصاريفك المعتادة",
    "Next date":
        "التاريخ التالي",
    "Next expected":
        "المتوقع التالي",
    "Next payment":
        "الدفعة التالية",
    "Next ›":
        "التالي ›",
    "No accounts yet":
        "لا توجد حسابات بعد",
    "No active subscriptions":
        "لا توجد اشتراكات نشطة",
    "No allocations yet — all of your money is Available.":
        "لا توجد مخصصات بعد — كل مالك متاح.",
    "No Anthropic API key. Add one in Settings or set {0}.":
        "لا يوجد مفتاح API من Anthropic. أضف واحداً في الإعدادات أو عيّن {0}.",
    "No API key yet. Keys are kept in {0}, never in the database.":
        "لا يوجد مفتاح API بعد. تُحفظ المفاتيح في {0}، وليس أبداً في قاعدة البيانات.",
    "No balance exists before the account's opening date ({0}).":
        "لا يوجد رصيد قبل تاريخ فتح الحساب ({0}).",
    "No budgets yet":
        "لا توجد ميزانيات بعد",
    "No category yet — add one first":
        "لا توجد فئة بعد — أضف واحدة أولاً",
    "No comparison: the comparison period ({0}) starts before tracking began on {1}.":
        "لا مقارنة: فترة المقارنة ({0}) تبدأ قبل بدء المتابعة في {1}.",
    "No comparison: {0} – {1} is before tracking began":
        "لا مقارنة: {0} – {1} قبل بدء المتابعة",
    "No contributions yet.":
        "لا توجد مساهمات بعد.",
    "No deadline":
        "دون موعد نهائي",
    "No expense categories yet — click New…":
        "لا توجد فئات مصاريف بعد — انقر على جديد…",
    "No expense categories yet.":
        "لا توجد فئات مصاريف بعد.",
    "No expenses recorded this month":
        "لا توجد مصاريف مسجلة هذا الشهر",
    "No free allocations":
        "لا توجد مخصصات حرة",
    "No goals yet":
        "لا توجد أهداف بعد",
    "No goals yet. Create one to set money aside for something that matters.":
        "لا توجد أهداف بعد. أنشئ هدفاً لتضع مالاً جانباً لشيء يهمك.",
    "No income in this period":
        "لا مداخيل في هذه الفترة",
    "No income or expenses recorded in the last months":
        "لا مداخيل ولا مصاريف مسجلة في الأشهر الأخيرة",
    "No income recorded yet this month":
        "لا مداخيل مسجلة هذا الشهر بعد",
    "No income recorded, so there is no savings rate.":
        "لا مداخيل مسجلة، لذلك لا توجد نسبة ادخار.",
    "No income was recorded while spending was {0}.":
        "لم تُسجَّل أي مداخيل بينما بلغت المصاريف {0}.",
    "No investment categories — click New…":
        "لا توجد فئات استثمار — انقر على جديد…",
    "No investments yet":
        "لا توجد استثمارات بعد",
    "No loans or debts recorded.":
        "لا توجد قروض أو ديون مسجلة.",
    "no local model (none chosen)":
        "لا يوجد نموذج محلي (لم يُختر أي نموذج)",
    "No matching transactions":
        "لا توجد عمليات مطابقة",
    "No payments due in the next 30 days.":
        "لا دفعات مستحقة في الأيام الثلاثين القادمة.",
    "No published version was found.":
        "لم يُعثر على أي إصدار منشور.",
    "No receipts yet.":
        "لا توجد إيصالات بعد.",
    "No recurring entries yet. Add your salary or rent to have them recorded for you.":
        "لا توجد عمليات متكررة بعد. أضف راتبك أو كراءك ليُسجَّلا عنك.",
    "No regular weekly or monthly expenses detected in the last 12 months.":
        "لم تُكتشف مصاريف أسبوعية أو شهرية منتظمة في آخر 12 شهراً.",
    "No return percentage: nothing is currently invested (withdrawals ≥ contributions).":
        "لا نسبة عائد: لا شيء مستثمر حالياً (المسحوبات ≥ المساهمات).",
    "No rules yet.":
        "لا توجد قواعد بعد.",
    "No safety copies yet.":
        "لا توجد نسخ أمان بعد.",
    "No spending in this or the previous period":
        "لا مصاريف في هذه الفترة ولا في السابقة",
    "No spending in this period":
        "لا مصاريف في هذه الفترة",
    "No spending recorded.":
        "لا مصاريف مسجلة.",
    "No subscriptions yet":
        "لا توجد اشتراكات بعد",
    "No transactions yet":
        "لا توجد عمليات بعد",
    "No transactions yet.":
        "لا توجد عمليات بعد.",
    "No value entered yet.":
        "لم تُدخل أي قيمة بعد.",
    "No {0} categories yet — click New…":
        "لا توجد فئات {0} بعد — انقر على جديد…",
    "None":
        "لا شيء",
    "Not changed: Windows Hello did not answer.":
        "لم يتغير شيء: لم يُجب Windows Hello.",
    "Not changed: Windows Hello did not confirm it's you.":
        "لم يتغير شيء: لم يؤكد Windows Hello هويتك.",
    "Not found in your data, so possibly wrong: ":
        "غير موجود في بياناتك، لذا قد يكون خاطئاً: ",
    "Not set aside for anything":
        "غير مخصص لأي شيء",
    "Not through an account (only track it)":
        "ليس عبر حساب (متابعة فقط)",
    "Not valued yet":
        "لم يُقيَّم بعد",
    "Note":
        "ملاحظة",
    "Notes":
        "ملاحظات",
    "Nothing due in this period.":
        "لا شيء مستحق في هذه الفترة.",
    "Nothing matches the current search and filters.":
        "لا شيء يطابق البحث وعوامل التصفية الحالية.",
    "Nothing owed":
        "لا ديون",
    "Nothing set aside yet":
        "لا شيء مخصص بعد",
    "Nothing set aside · as of {0}":
        "لا شيء مخصص · في {0}",
    "Nothing to compare with in the previous period":
        "لا شيء للمقارنة في الفترة السابقة",
    "Notifications":
        "الإشعارات",
    "Nov":
        "نونبر",
    "Oct":
        "أكتوبر",
    "Off":
        "متوقف",
    "Offline · stored on this computer · version {0}":
        "دون اتصال · مخزن على هذا الحاسوب · الإصدار {0}",
    "Offline · stored on this PC":
        "دون اتصال · مخزن على هذا الحاسوب",
    "Offset must be between zero and the number of records.":
        "يجب أن تكون الإزاحة بين الصفر وعدد السجلات.",
    "Ollama address":
        "عنوان Ollama",
    "Ollama did not answer within {0} seconds.":
        "لم يُجب Ollama خلال {0} ثانية.",
    "Ollama is not running at {0}. Start Ollama and try again.":
        "Ollama لا يعمل على {0}. شغّل Ollama وحاول مرة أخرى.",
    "Ollama returned an empty answer.":
        "أعاد Ollama إجابة فارغة.",
    "Ollama returned an error (HTTP {0}){1}.":
        "أعاد Ollama خطأ (HTTP {0}){1}.",
    "Ollama returned an error: {0}":
        "أعاد Ollama خطأ: {0}",
    "Ollama sent an unreadable answer.":
        "أرسل Ollama إجابة غير مقروءة.",
    "Ollama sent an unreadable model list.":
        "أرسل Ollama قائمة نماذج غير مقروءة.",
    "Ollama stopped before finishing the answer.":
        "توقف Ollama قبل إنهاء الإجابة.",
    "on this computer":
        "على هذا الحاسوب",
    "On track":
        "ضمن الحد",
    "Once you start recording transactions, this page will summarise your balance, how your money is allocated and how this month compares to the last.":
        "بمجرد أن تبدأ بتسجيل العمليات، ستلخص هذه الصفحة رصيدك وطريقة توزيع مالك ومقارنة هذا الشهر بالسابق.",
    "One column (minus = money out)":
        "عمود واحد (السالب = مال خارج)",
    "Online (Anthropic Claude)":
        "عبر الإنترنت (Anthropic Claude)",
    "Online AI (Anthropic) sends selected financial information — totals, rates, category spending and trends, never transaction descriptions or account names — to api.anthropic.com. You see exactly what would be sent and must confirm every request.":
        "الذكاء الاصطناعي عبر الإنترنت (Anthropic) يرسل معلومات مالية مختارة — المجاميع والنسب ومصاريف الفئات والاتجاهات، وليس أبداً أوصاف العمليات أو أسماء الحسابات — إلى api.anthropic.com. ترى بالضبط ما سيُرسَل ويجب أن تؤكد كل طلب.",
    "Online AI ({0}, Anthropic): each request sends a summary of your finances to {1}. You will see exactly what is sent and nothing leaves this computer until you confirm.{2}":
        "ذكاء اصطناعي عبر الإنترنت ({0}، Anthropic): كل طلب يرسل ملخصاً لماليتك إلى {1}. سترى بالضبط ما يُرسَل ولا يغادر شيء هذا الحاسوب حتى تؤكد.{2}",
    "Online AI sends a summary of your finances to Anthropic ({0}). Before every request you will see exactly what would be sent, and nothing is sent unless you confirm.":
        "الذكاء الاصطناعي عبر الإنترنت يرسل ملخصاً لماليتك إلى Anthropic ({0}). قبل كل طلب سترى بالضبط ما سيُرسَل، ولا يُرسَل شيء ما لم تؤكد.",
    "Only expense categories can be investment categories.":
        "فئات المصاريف وحدها يمكن أن تكون فئات استثمار.",
    "Only when I lock it":
        "فقط عندما أقفله",
    "Only {0} is left to repay.":
        "لم يتبقَّ للسداد سوى {0}.",
    "Open":
        "جارٍ",
    "Open data folder":
        "فتح مجلد البيانات",
    "Open Money Manager":
        "فتح Money Manager",
    "Open the AI Advisor":
        "فتح المستشار الذكي",
    "Open without the lock":
        "الفتح دون القفل",
    "Opening your data":
        "جارٍ فتح بياناتك",
    "Optional":
        "اختياري",
    "Optional — broker, wallet, where the gold is kept …":
        "اختياري — الوسيط، المحفظة، مكان حفظ الذهب …",
    "Optional, e.g. Cash for the market":
        "اختياري، مثلاً: نقود للسوق",
    "Other":
        "أخرى",
    "Over":
        "تجاوز",
    "Over budget":
        "تجاوز الميزانية",
    "Over the limit":
        "فوق الحد",
    "Over-allocated by {0}: allocations exceed your real balance. Move money from an allocation back to Available.":
        "مخصص بزيادة {0}: المخصصات تتجاوز رصيدك الفعلي. أعد المال من مخصص إلى المتاح.",
    "Overdue":
        "متأخر",
    "Overdue by 1 day":
        "متأخر بيوم واحد",
    "Overdue by {0} days":
        "متأخر بـ {0} أيام",
    "Overdue by {0} {1}":
        "متأخر بـ {0} {1}",
    "overdue since {0}":
        "متأخر منذ {0}",
    "Overspent":
        "تجاوز",
    "Overspent this month":
        "المصاريف تجاوزت المداخيل هذا الشهر",
    "Owed":
        "مستحق",
    "Owed to you: {0} · You owe: {1} · In your net worth: {2}":
        "يُدان لك: {0} · تدين به: {1} · في صافي ثروتك: {2}",
    "Page size must be between 1 and {0}.":
        "يجب أن يكون حجم الصفحة بين 1 و {0}.",
    "Paid from":
        "مدفوع من",
    "Paid from one of my accounts (records an investment expense)":
        "مدفوع من أحد حساباتي (يسجل مصروف استثمار)",
    "Paid from your accounts":
        "مدفوع من حساباتك",
    "Paid on":
        "تاريخ الدفع",
    "Password for the backup":
        "كلمة مرور النسخة الاحتياطية",
    "Paste an Anthropic API key":
        "الصق مفتاح API من Anthropic",
    "Pause":
        "إيقاف مؤقت",
    "Paused":
        "متوقف مؤقتاً",
    "Payment {0}":
        "دفعة {0}",
    "Per month":
        "شهرياً",
    "Period":
        "الفترة",
    "Personal finance, kept local":
        "مالية شخصية، محفوظة محلياً",
    "Personalised insights based on your own numbers.":
        "تحليلات مخصصة مبنية على أرقامك.",
    "Photos (JPG, PNG…) or PDFs up to {0} MB. They are kept with your data, included in backups, and deleted with the entry.":
        "صور (JPG، PNG…) أو ملفات PDF حتى {0} ميغابايت. تُحفظ مع بياناتك وتُضمَّن في النسخ الاحتياطية وتُحذف مع العملية.",
    "Planned this month":
        "المخطط هذا الشهر",
    "Portfolio value":
        "قيمة المحفظة",
    "positive balance adjustment":
        "تسوية موجبة للرصيد",
    "Pound sterling":
        "جنيه إسترليني",
    "Preferences and where your data is stored.":
        "التفضيلات ومكان تخزين بياناتك.",
    "Previous":
        "السابقة",
    "Previous period":
        "الفترة السابقة",
    "Previous period is before tracking began":
        "الفترة السابقة قبل بدء المتابعة",
    "Privacy":
        "الخصوصية",
    "processed on this computer":
        "تمت المعالجة على هذا الحاسوب",
    "Profit / loss":
        "الربح / الخسارة",
    "Progress":
        "التقدم",
    "Projected balance":
        "الرصيد المتوقع",
    "Projected balance: {0}":
        "الرصيد المتوقع: {0}",
    "Protect the backup with a password (encrypted)":
        "حماية النسخة الاحتياطية بكلمة مرور (مشفرة)",
    "Protected backup":
        "نسخة احتياطية محمية",
    "Protected Money Manager backup":
        "نسخة احتياطية محمية من Money Manager",
    "Provider":
        "المزود",
    "Put into":
        "وُضع في",
    "Python":
        "Python",
    "Qt / PySide6":
        "Qt / PySide6",
    "Question":
        "سؤال",
    "Question for the advisor":
        "سؤال للمستشار",
    "Quit Money Manager":
        "الخروج من Money Manager",
    "Ready":
        "جاهز",
    "Ready: {0} on this computer.":
        "جاهز: {0} على هذا الحاسوب.",
    "Recalculate the summary from your latest data.":
        "إعادة حساب الملخص من أحدث بياناتك.",
    "Receipt {0!r} does not exist.":
        "الإيصال {0!r} غير موجود.",
    "Receipts":
        "الإيصالات",
    "Receipts…":
        "الإيصالات…",
    "Received into":
        "استُلم في",
    "Recent moves":
        "آخر عمليات النقل",
    "Recent transactions":
        "آخر العمليات",
    "Record":
        "تسجيل",
    "Record a transaction":
        "تسجيل عملية",
    "Record contributions to your investments and see how they add up.":
        "سجّل مساهماتك في استثماراتك وشاهد مجموعها.",
    "Record how much you have saved for this goal outside the app. This amount is not part of your balance.":
        "سجّل كم ادخرت لهذا الهدف خارج التطبيق. هذا المبلغ ليس جزءاً من رصيدك.",
    "Record payment":
        "تسجيل الدفعة",
    "Record payment · {0}":
        "تسجيل الدفعة · {0}",
    "Record repayment…":
        "تسجيل سداد…",
    "Record withdrawal":
        "تسجيل سحب",
    "Record your first income or expense. Your balance updates automatically.":
        "سجّل أول دخل أو مصروف لك. يتحدّث رصيدك تلقائياً.",
    "Recorded automatically (recurring)":
        "مسجلة تلقائياً (متكررة)",
    "Recorded automatically on each date — when Money Manager is open, or the next time it starts. A first date in the past records the dates since then (up to a year).":
        "تُسجَّل تلقائياً في كل تاريخ — عندما يكون Money Manager مفتوحاً، أو عند تشغيله التالي. التاريخ الأول في الماضي يسجل التواريخ منذ ذلك الحين (حتى سنة).",
    "Recorded now: {0}.":
        "سُجّل الآن: {0}.",
    "Recording income and expenses with your own categories is coming in the next sprint.":
        "تسجيل المداخيل والمصاريف بفئاتك الخاصة قادم قريباً.",
    "Records one expense in the investment category, so your balance goes down and the statistics count it as investing.":
        "يسجل مصروفاً واحداً في فئة الاستثمار، فينخفض رصيدك وتحسبه الإحصائيات استثماراً.",
    "Recurring entries":
        "العمليات المتكررة",
    "Recurring entry {0!r} does not exist.":
        "العملية المتكررة {0!r} غير موجودة.",
    "recurring expense":
        "مصروف متكرر",
    "recurring expenses":
        "مصاريف متكررة",
    "Recurring spending":
        "المصاريف المتكررة",
    "Recurring…":
        "المتكررة…",
    "Refresh":
        "تحديث",
    "Regenerate":
        "إعادة التوليد",
    "Released when archived":
        "حُرِّر عند الأرشفة",
    "Remove":
        "حذف",
    "Remove budget":
        "حذف الميزانية",
    "Remove key":
        "حذف المفتاح",
    "Remove receipt":
        "حذف الإيصال",
    "Remove the budget for {0}?\n\nYour spending and the category itself are not affected.":
        "حذف ميزانية {0}؟\n\nلا تتأثر مصاريفك ولا الفئة نفسها.",
    "Remove the repayment of {0} on {1}? If it moved money through an account, that adjustment is removed too.":
        "حذف السداد بقيمة {0} في {1}؟ إذا نقل مالاً عبر حساب، فستُحذف تلك التسوية أيضاً.",
    "Remove {0}?":
        "حذف {0}؟",
    "Rename":
        "إعادة تسمية",
    "Rename allocation":
        "إعادة تسمية المخصص",
    "Renewing soon":
        "تجديدات قريبة",
    "Repaid":
        "مُسدَّد",
    "Repay by":
        "السداد قبل",
    "Repay {0}":
        "سداد {0}",
    "Repayment from {0}":
        "سداد من {0}",
    "Repayment recorded":
        "تم تسجيل السداد",
    "Repayment removed":
        "تم حذف السداد",
    "Repayment to {0}":
        "سداد إلى {0}",
    "Repayment {0!r} does not exist.":
        "السداد {0!r} غير موجود.",
    "Repeats":
        "التكرار",
    "Replace ALL current data with this backup from {0}?\n\nThe backup has {1} accounts, {2} transactions, {3} goals and {4} records in total (currency: {5}).\n\nYour current data is first saved to a safety backup next to the database.":
        "استبدال كل البيانات الحالية بهذه النسخة الاحتياطية من {0}؟\n\nتحتوي النسخة على {1} حسابات و{2} عمليات و{3} أهداف و{4} سجلاً إجمالاً (العملة: {5}).\n\nتُحفظ بياناتك الحالية أولاً في نسخة أمان بجانب قاعدة البيانات.",
    "Replace ALL current data with this safety copy?\n\n{0}\n\nYour current data is first saved as a new safety copy, so you can come back to it.":
        "استبدال كل البيانات الحالية بنسخة الأمان هذه؟\n\n{0}\n\nتُحفظ بياناتك الحالية أولاً كنسخة أمان جديدة، لتتمكن من العودة إليها.",
    "Replace my data":
        "استبدال بياناتي",
    "Report saved":
        "تم حفظ التقرير",
    "Reset all data":
        "إعادة ضبط كل البيانات",
    "Reset all data…":
        "إعادة ضبط كل البيانات…",
    "Reset application data":
        "إعادة ضبط بيانات التطبيق",
    "Reset complete":
        "اكتملت إعادة الضبط",
    "Restart now":
        "إعادة التشغيل الآن",
    "Restore":
        "استعادة",
    "Restore complete":
        "اكتملت الاستعادة",
    "Restore safety copy":
        "استعادة نسخة أمان",
    "restored":
        "مستعادة",
    "Restore…":
        "استعادة…",
    "Resume":
        "استئناف",
    "Return":
        "العائد",
    "Return calculated from your latest value.":
        "العائد محسوب من آخر قيمة لك.",
    "Return this money to where it came from":
        "إعادة هذا المال إلى مصدره",
    "Returns its money to Available":
        "يعيد ماله إلى المتاح",
    "rising":
        "مرتفعة",
    "Rule {0!r} does not exist.":
        "القاعدة {0!r} غير موجودة.",
    "Runs on this computer with Ollama. Nothing is sent over the internet.":
        "يعمل على هذا الحاسوب مع Ollama. لا يُرسَل شيء عبر الإنترنت.",
    "Safety copies":
        "نسخ الأمان",
    "safety copy":
        "نسخة الأمان",
    "Same as Windows":
        "مثل Windows",
    "Saturdays":
        "أيام السبت",
    "Saudi riyal":
        "ريال سعودي",
    "Save":
        "حفظ",
    "Save a copy automatically each day (the last 30 are kept)":
        "حفظ نسخة تلقائياً كل يوم (يُحتفظ بآخر 30)",
    "Save a month's summary as a PDF you can print or keep":
        "حفظ ملخص شهر كملف PDF للطباعة أو الحفظ",
    "Save a summary of a whole year as a PDF":
        "حفظ ملخص سنة كاملة كملف PDF",
    "Save AI settings":
        "حفظ إعدادات الذكاء الاصطناعي",
    "Save budget":
        "حفظ الميزانية",
    "Save changes":
        "حفظ التغييرات",
    "Save key":
        "حفظ المفتاح",
    "Save the monthly report":
        "حفظ التقرير الشهري",
    "Save value":
        "حفظ القيمة",
    "Save {0} per month to finish on time.":
        "ادخر {0} شهرياً للإنهاء في الموعد.",
    "Saved":
        "المدخر",
    "Saved so far":
        "المدخر حتى الآن",
    "Saved this month":
        "المدخر هذا الشهر",
    "Saved towards goals":
        "المدخر للأهداف",
    "Savings rate":
        "نسبة الادخار",
    "Savings rate {0}":
        "نسبة الادخار {0}",
    "Savings were {0}, {1} of income.":
        "بلغ الادخار {0}، أي {1} من المداخيل.",
    "Search description, notes, category or amount":
        "ابحث في الوصف أو الملاحظات أو الفئة أو المبلغ",
    "Search entries":
        "ابحث في العمليات",
    "Search text cannot be longer than {0} characters.":
        "لا يمكن أن يتجاوز نص البحث {0} حرفاً.",
    "Search transactions":
        "البحث في العمليات",
    "Search transactions: type and press Enter":
        "البحث في العمليات: اكتب ثم اضغط Enter",
    "See whether your spending and saving are improving.":
        "تحقق هل تتحسن مصاريفك وادخارك.",
    "selected period":
        "الفترة المختارة",
    "Send financial information to {0}?":
        "إرسال معلومات مالية إلى {0}؟",
    "Send to {0}":
        "إرسال إلى {0}",
    "Sending financial information to {0} needs your confirmation first.":
        "إرسال معلومات مالية إلى {0} يحتاج إلى تأكيدك أولاً.",
    "sent to Anthropic":
        "أُرسل إلى Anthropic",
    "Sep":
        "شتنبر",
    "Separate debit and credit columns":
        "عمودان منفصلان للمدين والدائن",
    "Set a deadline":
        "تحديد موعد نهائي",
    "Set a deadline to see how much to save each month.":
        "حدد موعداً نهائياً لترى كم تدخر كل شهر.",
    "Set a monthly limit for a spending category, such as groceries or eating out, and see at a glance how much is left this month.":
        "حدد حداً شهرياً لفئة مصاريف، مثل المشتريات أو المطاعم، وشاهد بنظرة كم تبقى هذا الشهر.",
    "Set a monthly limit for a spending category.":
        "حدد حداً شهرياً لفئة مصاريف.",
    "Set aside":
        "المخصص",
    "set aside":
        "مخصص",
    "Set aside now (from Available)":
        "التخصيص الآن (من المتاح)",
    "Set financial targets and track your progress.":
        "حدد أهدافاً مالية وتابع تقدمك.",
    "Set money aside for purposes; what is left is Available to spend.":
        "ضع المال جانباً لأغراض محددة؛ ما يتبقى متاح للإنفاق.",
    "Settings":
        "الإعدادات",
    "Settings → Updates → Download":
        "الإعدادات ← التحديثات ← تنزيل",
    "Share":
        "الحصة",
    "Share of this month's income you kept":
        "حصة مداخيل هذا الشهر التي احتفظت بها",
    "Share of your balance set aside in allocations":
        "حصة رصيدك الموضوعة في المخصصات",
    "Show archived":
        "عرض المؤرشفة",
    "Show reminders":
        "عرض التذكيرات",
    "Show the values as a table":
        "عرض القيم في جدول",
    "Show {0} as a table":
        "عرض {0} في جدول",
    "Showing {0}–{1} of {2}":
        "عرض {0}–{1} من {2}",
    "Simple indicators based on your own data":
        "مؤشرات بسيطة مبنية على بياناتك",
    "Since the start: in {0} · out {1}":
        "منذ البداية: دخل {0} · خرج {1}",
    "Skip":
        "تخطٍّ",
    "Skip payment":
        "تخطي الدفعة",
    "Skip the payment of “{0}” due {1}? No expense is recorded — use this if you already entered it or it was not charged.":
        "تخطي دفعة «{0}» المستحقة في {1}؟ لن يُسجَّل أي مصروف — استخدم هذا إذا أدخلتها سابقاً أو لم تُقتطع.",
    "Some lines were not imported":
        "لم يتم استيراد بعض الأسطر",
    "Something went wrong":
        "حدث خطأ ما",
    "Source":
        "المصدر",
    "Spending":
        "المصاريف",
    "Spending analysis":
        "تحليل المصاريف",
    "Spending by category":
        "المصاريف حسب الفئة",
    "Spending change compares with the previous month (the current month with the same days of last month).":
        "تغير المصاريف يُقارن بالشهر السابق (الشهر الحالي بنفس أيام الشهر الماضي).",
    "Spending goes to":
        "المصاريف تذهب إلى",
    "Spending per category, this period vs the previous one · {0}":
        "المصاريف لكل فئة، هذه الفترة مقابل السابقة · {0}",
    "Spending trend":
        "اتجاه المصاريف",
    "Spending vs last month":
        "المصاريف مقارنة بالشهر الماضي",
    "Spending vs prev.":
        "المصاريف مقابل السابق",
    "Spending was {0} of income.":
        "بلغت المصاريف {0} من المداخيل.",
    "Spent":
        "المصروف",
    "Spent so far":
        "المصروف حتى الآن",
    "SQLite":
        "SQLite",
    "Start date":
        "تاريخ البدء",
    "start must not be after end":
        "يجب ألا تكون البداية بعد النهاية",
    "Statement imported":
        "تم استيراد الكشف",
    "Statistics":
        "الإحصائيات",
    "Statistics are calculated from your recorded transactions. Add the account you want to track first.":
        "تُحسب الإحصائيات من العمليات المسجلة. أضف أولاً الحساب الذي تريد متابعته.",
    "statistics page":
        "صفحة الإحصائيات",
    "Status":
        "الحالة",
    "Stock":
        "أسهم",
    "Stop recording “{0}”? Entries already recorded are kept.":
        "إيقاف تسجيل «{0}»؟ تبقى العمليات المسجلة سابقاً.",
    "Stored API key removed.":
        "تم حذف مفتاح API المحفوظ.",
    "Stored only in your local database.":
        "محفوظ فقط في قاعدة بياناتك المحلية.",
    "Subscription payment due {0}":
        "دفعة اشتراك مستحقة في {0}",
    "Subscription {0!r} does not exist.":
        "الاشتراك {0!r} غير موجود.",
    "Subscriptions":
        "الاشتراكات",
    "Subscriptions & Bills":
        "الاشتراكات والفواتير",
    "Suggestions":
        "اقتراحات",
    "Summary":
        "الملخص",
    "Sundays":
        "أيام الأحد",
    "Swiss franc":
        "فرنك سويسري",
    "Table":
        "جدول",
    "Take out":
        "سحب",
    "Target":
        "الهدف",
    "Target ({0})":
        "المبلغ المستهدف ({0})",
    "Target reached":
        "تم بلوغ الهدف",
    "Test connection":
        "اختبار الاتصال",
    "The account '{0}' has transactions and cannot be deleted.":
        "الحساب «{0}» يحتوي على عمليات ولا يمكن حذفه.",
    "The account to transfer from does not exist.":
        "الحساب المحوَّل منه غير موجود.",
    "The account to transfer to does not exist.":
        "الحساب المحوَّل إليه غير موجود.",
    "The advisor explains figures calculated from your recorded transactions. Add the account you want to track first.":
        "يشرح المستشار أرقاماً محسوبة من عملياتك المسجلة. أضف أولاً الحساب الذي تريد متابعته.",
    "The AI request failed unexpectedly.":
        "فشل طلب الذكاء الاصطناعي بشكل غير متوقع.",
    "The allocation '{0}' already holds the money for the goal '{1}'. Money can count towards only one goal.":
        "المخصص «{0}» يحتوي بالفعل على مال الهدف «{1}». يمكن أن يُحسب المال لهدف واحد فقط.",
    "The allocation '{0}' has a negative balance; run a consistency check.":
        "المخصص «{0}» رصيده سالب؛ شغّل فحص الاتساق.",
    "The allocation '{0}' has transfers or transactions; archive it instead.":
        "المخصص «{0}» لديه تحويلات أو عمليات؛ أرشفه بدلاً من ذلك.",
    "The allocation '{0}' holds the money for the goal '{1}'; delete the goal first.":
        "المخصص «{0}» يحتوي على مال الهدف «{1}»؛ احذف الهدف أولاً.",
    "The allocation '{0}' holds {1}; this change would leave it at {2}. Move money into it first, or record the transaction against Available.":
        "المخصص «{0}» يحتوي على {1}؛ هذا التغيير سيتركه عند {2}. انقل مالاً إليه أولاً، أو سجّل العملية على المتاح.",
    "The allocation '{0}' is archived, and this change would put money back into it. Restore the allocation first, or record the transaction against Available.":
        "المخصص «{0}» مؤرشف، وهذا التغيير سيعيد مالاً إليه. استعد المخصص أولاً، أو سجّل العملية على المتاح.",
    "The allocation '{0}' is archived.":
        "المخصص «{0}» مؤرشف.",
    "The allocation '{0}' is archived; restore it before undoing.":
        "المخصص «{0}» مؤرشف؛ استعده قبل التراجع.",
    "The allocation '{0}' is negative ({1}).":
        "المخصص «{0}» سالب ({1}).",
    "The amount and the date stay as recorded; repayments lower what is left.":
        "يبقى المبلغ والتاريخ كما سُجّلا؛ دفعات السداد تخفض المتبقي.",
    "The amount cannot be negative.":
        "لا يمكن أن يكون المبلغ سالباً.",
    "The answer could not be saved: {0}":
        "تعذّر حفظ الإجابة: {0}",
    "The archived allocation '{0}' still holds {1}.":
        "المخصص المؤرشف «{0}» لا يزال يحتوي على {1}.",
    "The backup could not be verified after writing it.":
        "تعذّر التحقق من النسخة الاحتياطية بعد كتابتها.",
    "the backup format version is not supported.":
        "إصدار صيغة النسخة الاحتياطية غير مدعوم.",
    "The backup from {0} was imported.":
        "تم استيراد النسخة الاحتياطية من {0}.",
    "The balance changed by {0}{1} from {2}.":
        "تغير الرصيد بمقدار {0}{1} منذ {2}.",
    "The balance history appears after your first days of tracking":
        "يظهر تاريخ الرصيد بعد أيامك الأولى من المتابعة",
    "The category '{0}' is archived.":
        "الفئة «{0}» مؤرشفة.",
    "The category '{0}' is used by a subscription; change the subscription's category first.":
        "الفئة «{0}» مستخدمة في اشتراك؛ غيّر فئة الاشتراك أولاً.",
    "The category '{0}' is used by transactions; archive it instead.":
        "الفئة «{0}» مستخدمة في عمليات؛ أرشفها بدلاً من ذلك.",
    "The check failed.":
        "فشل التحقق.",
    "The configuration file named by {0} does not exist: {1}":
        "ملف الإعداد المحدد بـ {0} غير موجود: {1}",
    "The currency can only be changed before any account exists, because Money Manager never converts amounts between currencies.":
        "لا يمكن تغيير العملة إلا قبل إنشاء أي حساب، لأن Money Manager لا يحوّل المبالغ أبداً بين العملات.",
    "The dashboard summarises your real balance, income, spending and allocations. Add the account you want to track first.":
        "تلخص لوحة القيادة رصيدك الفعلي ومداخيلك ومصاريفك ومخصصاتك. أضف أولاً الحساب الذي تريد متابعته.",
    "The data you had before was saved to:\n{0}":
        "حُفظت البيانات التي كانت لديك في:\n{0}",
    "The deadline cannot be in the past.":
        "لا يمكن أن يكون الموعد النهائي في الماضي.",
    "The deadline has passed. Edit the goal to set a new one.":
        "انقضى الموعد النهائي. عدّل الهدف لتحديد موعد جديد.",
    "The deadline must be within {0} years.":
        "يجب أن يكون الموعد النهائي خلال {0} سنة.",
    "The due date cannot be before the start date.":
        "لا يمكن أن يسبق موعد السداد تاريخ البدء.",
    "The file has no lines to import.":
        "لا يحتوي الملف على أي سطر للاستيراد.",
    "the file is damaged or was edited (checksum mismatch).":
        "الملف تالف أو تم تعديله (عدم تطابق المجموع الاختباري).",
    "The file is empty.":
        "الملف فارغ.",
    "The file is larger than {0} MB.":
        "الملف أكبر من {0} ميغابايت.",
    "the file is not readable JSON.":
        "الملف ليس JSON مقروءاً.",
    "The file is too large for a bank statement.":
        "الملف كبير جداً بالنسبة لكشف حساب بنكي.",
    "the file is too large.":
        "الملف كبير جداً.",
    "the file was not exported by Money Manager.":
        "لم يصدّر Money Manager هذا الملف.",
    "The file's contents do not match its type.":
        "محتوى الملف لا يطابق نوعه.",
    "The file's text encoding is not supported.":
        "ترميز نص الملف غير مدعوم.",
    "The first date cannot be before the account was opened ({0}).":
        "لا يمكن أن يسبق التاريخ الأول فتح الحساب ({0}).",
    "The first date cannot be more than a year ago.":
        "لا يمكن أن يعود التاريخ الأول لأكثر من سنة.",
    "The first date must be within {0} years.":
        "يجب أن يكون التاريخ الأول خلال {0} سنوات.",
    "The forecast appears once you have an account":
        "يظهر التوقع بمجرد أن يكون لديك حساب",
    "The information to send changed after you agreed. Review it and confirm again.":
        "تغيرت المعلومات المراد إرسالها بعد موافقتك. راجعها وأكّد مرة أخرى.",
    "The initial amount cannot be negative.":
        "لا يمكن أن يكون المبلغ الأولي سالباً.",
    "The line has no amount.":
        "السطر لا يحتوي على مبلغ.",
    "The line has too few columns.":
        "السطر يحتوي على أعمدة قليلة جداً.",
    "the local model ({0}) when Ollama is running":
        "النموذج المحلي ({0}) عندما يعمل Ollama",
    "The lock is off.":
        "القفل متوقف.",
    "The lock is on.":
        "القفل مفعّل.",
    "The model '{0}' is not installed in Ollama. Run 'ollama pull {1}' first.":
        "النموذج «{0}» غير مثبت في Ollama. شغّل أولاً «ollama pull {1}».",
    "The model '{0}' is not installed. Run 'ollama pull {1}'.":
        "النموذج «{0}» غير مثبت. شغّل «ollama pull {1}».",
    "The model '{0}' was not found at Anthropic.":
        "لم يُعثر على النموذج «{0}» لدى Anthropic.",
    "The model name is not valid.":
        "اسم النموذج غير صالح.",
    "The next payment date cannot be more than a year in the past.":
        "لا يمكن أن يعود تاريخ الدفعة التالية لأكثر من سنة.",
    "The next payment date must be within {0} years.":
        "يجب أن يكون تاريخ الدفعة التالية خلال {0} سنوات.",
    "The next payment of '{0}' to confirm is the one due {1}.":
        "الدفعة التالية لـ «{0}» التي يجب تأكيدها هي المستحقة في {1}.",
    "The online provider needs the optional 'anthropic' package. Install it with pip install \"money-manager[ai-online]\".":
        "المزود عبر الإنترنت يحتاج إلى الحزمة الاختيارية «anthropic». ثبّتها بالأمر pip install \"money-manager[ai-online]\".",
    "The opening date cannot be after the account's first transaction ({0}).":
        "لا يمكن أن يكون تاريخ الفتح بعد أول عملية في الحساب ({0}).",
    "The password is wrong, or the file is damaged.":
        "كلمة المرور خاطئة، أو الملف تالف.",
    "The payment of '{0}' due {1} has already been confirmed.":
        "دفعة «{0}» المستحقة في {1} مؤكدة بالفعل.",
    "The period cannot end in the future.":
        "لا يمكن أن تنتهي الفترة في المستقبل.",
    "The period cannot start before {0}.":
        "لا يمكن أن تبدأ الفترة قبل {0}.",
    "The port number is not valid.":
        "رقم المنفذ غير صالح.",
    "The provider declined to answer this request.":
        "رفض المزود الإجابة عن هذا الطلب.",
    "The provider returned an empty answer.":
        "أعاد المزود إجابة فارغة.",
    "The range cannot end in the future.":
        "لا يمكن أن تنتهي الفترة في المستقبل.",
    "The range cannot start before {0}.":
        "لا يمكن أن تبدأ الفترة قبل {0}.",
    "The report could not be written to {0}.":
        "تعذّرت كتابة التقرير في {0}.",
    "The saved API key was removed.":
        "تم حذف مفتاح API المحفوظ.",
    "The selected account does not exist.":
        "الحساب المختار غير موجود.",
    "The selected allocation does not exist.":
        "المخصص المختار غير موجود.",
    "The selected category does not exist.":
        "الفئة المختارة غير موجودة.",
    "The source and destination must be different.":
        "يجب أن يختلف المصدر عن الوجهة.",
    "The start date must not be after the end date.":
        "يجب ألا يكون تاريخ البدء بعد تاريخ الانتهاء.",
    "The summary below is processed by {0} running on this computer. Nothing is sent over the internet.":
        "يعالج {0} الملخص أدناه على هذا الحاسوب. لا يُرسَل شيء عبر الإنترنت.",
    "the table '{0}' does not have the expected columns.":
        "الجدول «{0}» لا يحتوي على الأعمدة المتوقعة.",
    "The timeout must be between {0} and {1} seconds.":
        "يجب أن تكون المهلة بين {0} و {1} ثانية.",
    "The two passwords are different. Nothing was exported.":
        "كلمتا المرور مختلفتان. لم يُصدَّر شيء.",
    "The update server answered with an error ({0}).":
        "أجاب خادم التحديثات بخطأ ({0}).",
    "The update server sent an unexpected answer.":
        "أرسل خادم التحديثات إجابة غير متوقعة.",
    "The whole year":
        "السنة كاملة",
    "The Windows Credential Manager is only available on Windows.":
        "مدير بيانات الاعتماد متاح فقط على Windows.",
    "The {0} could not be {1}; your data was not changed.":
        "فشلت العملية ({0}): لم يتم {1}؛ لم تتغير بياناتك.",
    "The {0}'s records do not fit together (broken references). Nothing was {1}.":
        "سجلات ({0}) غير متطابقة (مراجع مكسورة). لم يتم {1}.",
    "Theme":
        "السمة",
    "There is no financial data to analyse yet. Create an account and record some transactions first.":
        "لا توجد بيانات مالية لتحليلها بعد. أنشئ حساباً وسجّل بعض العمليات أولاً.",
    "This allocation holds a goal's money; manage it on the Goals page":
        "هذا المخصص يحتوي على مال هدف؛ أدره من صفحة الأهداف",
    "This analysis and task were given to the AI ":
        "أُعطي هذا التحليل وهذه المهمة للذكاء الاصطناعي ",
    "This API key is not allowed to use the model.":
        "مفتاح API هذا غير مسموح له باستخدام النموذج.",
    "This backup is protected by a password.":
        "هذه النسخة الاحتياطية محمية بكلمة مرور.",
    "This backup is protected. Password:":
        "هذه النسخة الاحتياطية محمية. كلمة المرور:",
    "This backup was made with a newer version of Money Manager (data schema {0}). Update Money Manager to import it.":
        "صُنعت هذه النسخة الاحتياطية بإصدار أحدث من Money Manager (مخطط البيانات {0}). حدّث Money Manager لاستيرادها.",
    "This category has no budget.":
        "هذه الفئة ليس لها ميزانية.",
    "this computer":
        "هذا الحاسوب",
    "This deletes every account, transaction, allocation, goal, subscription, investment, setting and AI insight. A safety backup of the database is written next to it first. Export a backup yourself if you want to keep a copy elsewhere.":
        "هذا يحذف كل الحسابات والعمليات والمخصصات والأهداف والاشتراكات والاستثمارات والإعدادات وتحليلات الذكاء الاصطناعي. تُكتب أولاً نسخة أمان من قاعدة البيانات بجانبها. صدّر نسخة احتياطية بنفسك إن أردت الاحتفاظ بنسخة في مكان آخر.",
    "This does not look like an API key.":
        "هذا لا يبدو مفتاح API.",
    "This entry":
        "هذه العملية",
    "This entry is one side of a transfer between your accounts. Delete the transfer to remove both sides; to change it, delete it and record it again.":
        "هذه العملية أحد طرفي تحويل بين حساباتك. احذف التحويل لإزالة الطرفين؛ ولتغييره، احذفه ثم سجّله من جديد.",
    "This entry is one side of a transfer between your accounts. To change it, delete the transfer and record it again.":
        "هذه العملية أحد طرفي تحويل بين حساباتك. لتغييرها، احذف التحويل ثم سجّله من جديد.",
    "This expense is an investment contribution and must stay an expense. Delete it on the Investments page instead.":
        "هذا المصروف مساهمة في استثمار ويجب أن يبقى مصروفاً. احذفه من صفحة الاستثمارات بدلاً من ذلك.",
    "This goal's progress is the balance of its allocation; add or withdraw money instead.":
        "تقدم هذا الهدف هو رصيد مخصصه؛ أضف مالاً أو اسحبه بدلاً من ذلك.",
    "This insight no longer exists.":
        "هذا التحليل لم يعد موجوداً.",
    "This is not a valid Money Manager backup: {0}":
        "هذه ليست نسخة احتياطية صالحة من Money Manager: {0}",
    "This is version {0}. Money Manager can ask GitHub once a day whether a newer version exists. Only that question is sent — nothing about you or your data (GitHub sees your IP address, as with any web request). Nothing is downloaded by itself.":
        "هذا هو الإصدار {0}. يمكن لـ Money Manager أن يسأل GitHub مرة في اليوم هل يوجد إصدار أحدث. هذا السؤال وحده يُرسَل — لا شيء عنك ولا عن بياناتك (يرى GitHub عنوان IP الخاص بك، كما في أي طلب ويب). لا يُنزَّل شيء تلقائياً.",
    "This model runs on Ollama's servers, not on this computer. Choose a local model.":
        "هذا النموذج يعمل على خوادم Ollama، وليس على هذا الحاسوب. اختر نموذجاً محلياً.",
    "This month":
        "هذا الشهر",
    "This month · top 5, the rest grouped as Other":
        "هذا الشهر · أكبر 5، والباقي ضمن «أخرى»",
    "This payment is not due until {0}; it can be confirmed at most {1} days early.":
        "هذه الدفعة غير مستحقة قبل {0}؛ يمكن تأكيدها قبل {1} أيام على الأكثر.",
    "This period":
        "هذه الفترة",
    "This safety copy cannot be read.":
        "نسخة الأمان هذه غير مقروءة.",
    "This safety copy cannot be restored: {0}":
        "لا يمكن استعادة نسخة الأمان هذه: {0}",
    "This safety copy is damaged and cannot be restored.":
        "نسخة الأمان هذه تالفة ولا يمكن استعادتها.",
    "This year":
        "هذه السنة",
    "Thursdays":
        "أيام الخميس",
    "Tick the expense categories where money goes into investments (stocks, retirement funds, …). They count towards your investment rate and as saving rather than spending.":
        "حدد فئات المصاريف التي يذهب فيها المال إلى الاستثمار (أسهم، صناديق تقاعد، …). تُحسب في نسبة استثمارك وكادخار لا كإنفاق.",
    "Tiles rise into place, figures count up, bars and rings fill, and a short notice confirms each change. Switch off for a still interface.":
        "تظهر البطاقات في مكانها، وتعدّ الأرقام تصاعدياً، وتمتلئ الأشرطة والحلقات، ويؤكد إشعار قصير كل تغيير. أوقفها لواجهة ثابتة.",
    "Timeout":
        "المهلة",
    "To":
        "إلى",
    "To date":
        "إلى تاريخ",
    "To keep the data somewhere else (for example a portable drive), set data_dir in MoneyManager.ini next to MoneyManager.exe, or start Money Manager with the environment variable MONEY_MANAGER_DATA_DIR set to that folder. The folder cannot be moved from inside the app, so that data is never lost halfway through a move; use Export backup and Import backup to copy data between folders.":
        "للاحتفاظ بالبيانات في مكان آخر (مثلاً قرص محمول)، عيّن data_dir في MoneyManager.ini بجانب MoneyManager.exe، أو شغّل Money Manager مع متغير البيئة MONEY_MANAGER_DATA_DIR مضبوطاً على ذلك المجلد. لا يمكن نقل المجلد من داخل التطبيق، حتى لا تضيع البيانات أبداً في منتصف النقل؛ استخدم تصدير واستيراد نسخة احتياطية لنسخ البيانات بين المجلدات.",
    "To meet every deadline":
        "للوفاء بكل المواعيد",
    "To {0}":
        "إلى {0}",
    "Today":
        "اليوم",
    "Tomorrow":
        "غداً",
    "Total balance":
        "الرصيد الإجمالي",
    "Total balance at the end of each day":
        "الرصيد الإجمالي في نهاية كل يوم",
    "Total balance mismatch: {0} vs {1}.":
        "عدم تطابق الرصيد الإجمالي: {0} مقابل {1}.",
    "Track stocks, ETFs, crypto, gold or anything else: record what you put in and, from time to time, what it is worth. Profit and return appear once a value is entered.":
        "تابع الأسهم وصناديق المؤشرات والعملات المشفرة والذهب أو أي شيء آخر: سجّل ما تضعه فيه، ومن حين لآخر قيمته. يظهر الربح والعائد بمجرد إدخال قيمة.",
    "Track subscriptions and bills, their billing cycles and upcoming due dates.":
        "تابع الاشتراكات والفواتير ودورات فوترتها ومواعيدها القادمة.",
    "Tracked manually — not part of your balance":
        "متابَع يدوياً — ليس جزءاً من رصيدك",
    "Tracked manually — not part of your balance.":
        "متابَع يدوياً — ليس جزءاً من رصيدك.",
    "Tracked since {0} · opening balance {1}":
        "متابَع منذ {0} · الرصيد الافتتاحي {1}",
    "Transaction {0!r} does not exist.":
        "العملية {0!r} غير موجودة.",
    "Transactions":
        "العمليات",
    "Transactions are recorded against an account, such as your bank account or cash. Enter its current balance and start tracking from today.":
        "تُسجَّل العمليات على حساب، مثل حسابك البنكي أو نقودك. أدخل رصيده الحالي وابدأ المتابعة من اليوم.",
    "Transactions → Recurring…":
        "العمليات ← المتكررة…",
    "Transfer":
        "تحويل",
    "Transfer between accounts":
        "تحويل بين الحسابات",
    "Transfer between your accounts: {0}":
        "تحويل بين حساباتك: {0}",
    "Transfer deleted":
        "تم حذف التحويل",
    "Transfer from {0}":
        "تحويل من {0}",
    "Transfer in":
        "تحويل وارد",
    "Transfer out":
        "تحويل صادر",
    "Transfer recorded":
        "تم تسجيل التحويل",
    "Transfer to {0}":
        "تحويل إلى {0}",
    "Transfer {0!r} does not exist.":
        "التحويل {0!r} غير موجود.",
    "Transfers cannot be edited":
        "لا يمكن تعديل التحويلات",
    "Transfers move money between them":
        "التحويلات تنقل المال بينها",
    "Tuesdays":
        "أيام الثلاثاء",
    "Turn off the Money Manager lock":
        "إيقاف قفل Money Manager",
    "Turn on the Money Manager lock":
        "تفعيل قفل Money Manager",
    "Type":
        "النوع",
    "Type a question about your finances.":
        "اكتب سؤالاً عن ماليتك.",
    "Type the password again:":
        "اكتب كلمة المرور مرة أخرى:",
    "Type {0} to confirm":
        "اكتب {0} للتأكيد",
    "Type {0} to confirm.":
        "اكتب {0} للتأكيد.",
    "type|Expense":
        "مصروف",
    "type|Income":
        "دخل",
    "Typical amount":
        "المبلغ المعتاد",
    "UAE dirham":
        "درهم إماراتي",
    "Uncategorised":
        "دون فئة",
    "Undo":
        "تراجع",
    "Undo last repayment":
        "التراجع عن آخر سداد",
    "Undo move":
        "التراجع عن النقل",
    "Undo repayment":
        "التراجع عن السداد",
    "Undo this move?\n\n{0} · {1} · {2}":
        "التراجع عن هذا النقل؟\n\n{0} · {1} · {2}",
    "Unknown fill colour: {0!r}":
        "لون تعبئة غير معروف: {0!r}",
    "Unknown page: {0!r}":
        "صفحة غير معروفة: {0!r}",
    "Unknown setting(s) {0} in '{1}'; expected {2}.":
        "إعداد(ات) غير معروفة {0} في «{1}»؛ المتوقع {2}.",
    "Unlock Money Manager":
        "فتح قفل Money Manager",
    "Unlock was cancelled. Choose Unlock to try again.":
        "تم إلغاء فتح القفل. اختر فتح القفل للمحاولة مرة أخرى.",
    "Unlock with Windows Hello":
        "فتح القفل عبر Windows Hello",
    "Unsupported amount type: {0}.":
        "نوع مبلغ غير مدعوم: {0}.",
    "Unsupported value type {0}":
        "نوع قيمة غير مدعوم {0}",
    "Upcoming payments":
        "الدفعات القادمة",
    "Update amount":
        "تحديث المبلغ",
    "Update the values of your investments to see returns":
        "حدّث قيم استثماراتك لترى العوائد",
    "Update value":
        "تحديث القيمة",
    "Update value · {0}":
        "تحديث القيمة · {0}",
    "Update {0}":
        "تحديث {0}",
    "Updates":
        "التحديثات",
    "Updating…":
        "جارٍ التحديث…",
    "US dollar":
        "دولار أمريكي",
    "Use a password of at least {0} characters.":
        "استخدم كلمة مرور من {0} أحرف على الأقل.",
    "Use either a comma or a dot for decimals, and spaces to group thousands.":
        "استخدم إما الفاصلة أو النقطة للكسور العشرية، والمسافات لفصل الآلاف.",
    "Use this currency":
        "استخدام هذه العملة",
    "Used after a restart.":
        "يُطبَّق بعد إعادة التشغيل.",
    "Using the key ending in {0} from {1}.":
        "استخدام المفتاح المنتهي بـ {0} من {1}.",
    "Usual income {0} and spending {1} a month (last {2} complete months), plus everything scheduled.":
        "المداخيل المعتادة {0} والمصاريف {1} شهرياً (آخر {2} أشهر كاملة)، إضافة إلى كل ما هو مبرمج.",
    "Usually paid from":
        "يُدفع عادة من",
    "Valuation {0!r} does not exist.":
        "التقييم {0!r} غير موجود.",
    "Value":
        "القيمة",
    "Value by type":
        "القيمة حسب النوع",
    "Value history":
        "تاريخ القيم",
    "Value on":
        "القيمة في",
    "Values are entered by you — the app does not fetch market prices.":
        "القيم تُدخلها أنت — التطبيق لا يجلب أسعار السوق.",
    "Version":
        "الإصدار",
    "Version {0}":
        "الإصدار {0}",
    "Version {0} is available (you have {1}).":
        "الإصدار {0} متاح (لديك {1}).",
    "View all":
        "عرض الكل",
    "vs {0}":
        "مقابل {0}",
    "vs {0} in {1}":
        "مقابل {0} في {1}",
    "Waiting for Windows Hello…":
        "في انتظار Windows Hello…",
    "Warning: some allocation balances in the imported data do not add up. Check the Money / Allocations page.":
        "تنبيه: بعض أرصدة المخصصات في البيانات المستوردة غير متطابقة. تحقق من صفحة المال / المخصصات.",
    "Warning: some allocation balances in the restored data do not add up. Check the Money / Allocations page.":
        "تنبيه: بعض أرصدة المخصصات في البيانات المستعادة غير متطابقة. تحقق من صفحة المال / المخصصات.",
    "was unchanged":
        "بقي دون تغيير",
    "Wednesdays":
        "أيام الأربعاء",
    "Week":
        "أسبوع",
    "Weekly":
        "أسبوعياً",
    "Weekly, on {0}":
        "أسبوعياً، {0}",
    "Well done — this goal is fully funded.":
        "أحسنت — هذا الهدف ممول بالكامل.",
    "were unchanged":
        "بقيت دون تغيير",
    "What":
        "ماذا",
    "What the AI received":
        "ما تلقاه الذكاء الاصطناعي",
    "What you have":
        "ما تملكه",
    "What you owe":
        "ما تدين به",
    "When a bank statement is imported, a line whose description contains a keyword goes to that keyword's category. Rules are learned when you change an entry's category; you can also add them here.":
        "عند استيراد كشف حساب بنكي، يذهب كل سطر يحتوي وصفه على كلمة مفتاحية إلى فئة تلك الكلمة. تُتعلَّم القواعد عندما تغيّر فئة عملية؛ ويمكنك أيضاً إضافتها هنا.",
    "When to lock":
        "متى يُقفَل",
    "Where is the money kept?":
        "أين يُحفظ المال؟",
    "Where the money went":
        "أين ذهب المال",
    "Where your balance is heading":
        "إلى أين يتجه رصيدك",
    "Where your money is kept, and how much is in each account.":
        "أين يُحفظ مالك، وكم في كل حساب.",
    "Who or what":
        "من أو ماذا",
    "Windows Hello could not confirm it's you. Try again.":
        "لم يتمكن Windows Hello من تأكيد هويتك. حاول مرة أخرى.",
    "Windows Hello did not answer.":
        "لم يُجب Windows Hello.",
    "Windows Hello is not available on this computer.":
        "Windows Hello غير متاح على هذا الحاسوب.",
    "Windows Hello is not set up for your account. Add a PIN, fingerprint or face in Windows Settings → Accounts → Sign-in options.":
        "Windows Hello غير مُعَدّ لحسابك. أضف رمز PIN أو بصمة أو الوجه في إعدادات Windows ← الحسابات ← خيارات تسجيل الدخول.",
    "Windows Hello is ready.":
        "Windows Hello جاهز.",
    "Windows notifications for payments due today or tomorrow, budgets near or over their limit, loans to repay within three days, and a balance projected below zero in the next 30 days. Each reminder is shown once, while Money Manager is running.":
        "إشعارات Windows للدفعات المستحقة اليوم أو غداً، والميزانيات القريبة من حدها أو المتجاوزة له، والقروض الواجب سدادها خلال ثلاثة أيام، ورصيد متوقع تحت الصفر في الأيام الثلاثين القادمة. يُعرض كل تذكير مرة واحدة، أثناء عمل Money Manager.",
    "Windows' \"Show animations in Windows\" setting is off, so Money Manager stays still as well.":
        "إعداد Windows «عرض الحركات في Windows» متوقف، لذلك يبقى Money Manager ثابتاً أيضاً.",
    "Withdraw":
        "سحب",
    "Withdraw from {0}":
        "سحب من {0}",
    "Withdrawal":
        "سحب",
    "withdrawal":
        "السحب",
    "Year:":
        "السنة:",
    "Yearly":
        "سنوياً",
    "Yearly report":
        "التقرير السنوي",
    "Yearly report…":
        "التقرير السنوي…",
    "Yearly, {0}":
        "سنوياً، {0}",
    "You cannot withdraw more than the goal's recorded amount.":
        "لا يمكنك سحب أكثر من المبلغ المسجل للهدف.",
    "You have the latest version ({0}).":
        "لديك أحدث إصدار ({0}).",
    "You kept <b>{0}</b> of your income (income − spending; money invested counts as kept).":
        "احتفظت بـ <b>{0}</b> من مداخيلك (المداخيل − المصاريف؛ المال المستثمر يُحسب محتفظاً به).",
    "You kept <b>{0}</b> of your income.":
        "احتفظت بـ <b>{0}</b> من مداخيلك.",
    "You spent <b>{0}</b> more than your income.":
        "أنفقت <b>{0}</b> أكثر من مداخيلك.",
    "You will be able to reserve money for savings, bills, investments and more. Moving money between allocations never changes your total balance.":
        "ستتمكن من حجز المال للادخار والفواتير والاستثمارات وغير ذلك. نقل المال بين المخصصات لا يغير رصيدك الإجمالي أبداً.",
    "Your accounts use {0}. The currency cannot be changed once accounts exist, because Money Manager never converts amounts between currencies.":
        "حساباتك تستخدم {0}. لا يمكن تغيير العملة بعد وجود حسابات، لأن Money Manager لا يحوّل المبالغ أبداً بين العملات.",
    "Your balance is projected at {0} on {1}.":
        "رصيدك المتوقع {0} في {1}.",
    "Your data from {0} was restored.":
        "تمت استعادة بياناتك من {0}.",
    "Your financial data is stored only on this computer, in the database file shown above. Money Manager has no user account, no cloud sync and no telemetry.":
        "بياناتك المالية مخزنة فقط على هذا الحاسوب، في ملف قاعدة البيانات المعروض أعلاه. ليس لدى Money Manager حساب مستخدم ولا مزامنة سحابية ولا قياس عن بعد.",
    "Your financial data is stored only on this computer.":
        "بياناتك المالية مخزنة فقط على هذا الحاسوب.",
    "Your financial overview at a glance.":
        "نظرة عامة على ماليتك.",
    "Your net worth over time appears after your first month":
        "يظهر تطور صافي ثروتك بعد شهرك الأول",
    "Your overview will live here":
        "ستظهر نظرتك العامة هنا",
    "Your previous data was saved to:\n{0}":
        "حُفظت بياناتك السابقة في:\n{0}",
    "{0!r} is not a valid amount.":
        "{0!r} ليس مبلغاً صالحاً.",
    "{0}\nPrevious: {1}":
        "{0}\nالسابقة: {1}",
    "{0}\nThis period: {1}\n{2}":
        "{0}\nهذه الفترة: {1}\n{2}",
    "{0} (to date)":
        "{0} (حتى اليوم)",
    "{0} added · {1} already recorded":
        "{0} مضافة · {1} مسجلة سابقاً",
    "{0} could not start":
        "تعذّر تشغيل {0}",
    "{0} failed unexpectedly. Please try again.":
        "فشل {0} بشكل غير متوقع. يرجى المحاولة مرة أخرى.",
    "{0} holds {1}; cannot move {2}.":
        "{0} يحتوي على {1}؛ لا يمكن نقل {2}.",
    "{0} left this month":
        "{0} متبقية هذا الشهر",
    "{0} new · {1} already recorded · {2} cannot be read":
        "{0} جديدة · {1} مسجلة سابقاً · {2} غير مقروءة",
    "{0} of income":
        "{0} من المداخيل",
    "{0} of what you have":
        "{0} مما تملكه",
    "{0} of your total balance":
        "{0} من رصيدك الإجمالي",
    "{0} of {1} investments valued":
        "{0} من {1} استثمارات مقيّمة",
    "{0} of {1} up to date":
        "{0} من {1} محدّثة",
    "{0} Open AI settings to set it up.":
        "{0} افتح إعدادات الذكاء الاصطناعي لإعداده.",
    "{0} over the last {1} complete months: {2}":
        "{0} خلال آخر {1} أشهر كاملة: {2}",
    "{0} over the limit":
        "{0} فوق الحد",
    "{0} per month":
        "{0} شهرياً",
    "{0} per year":
        "{0} سنوياً",
    "{0} receipts attached":
        "{0} إيصالات مرفقة",
    "{0} recurring entries recorded":
        "سُجّلت {0} عمليات متكررة",
    "{0} recurring expenses detected, about {1} per month{2}; {3} not tracked as subscriptions.":
        "اكتُشفت {0} مصاريف متكررة، حوالي {1} شهرياً{2}؛ {3} غير متابَعة كاشتراكات.",
    "{0} repays":
        "{0} يسدد",
    "{0} spending of {1} has no history in the previous {2} periods.":
        "مصاريف {0} بقيمة {1} ليس لها سجل في الفترات الـ {2} السابقة.",
    "{0} spending of {1} is {2}x its average of {3} over the previous {4} periods.":
        "مصاريف {0} بقيمة {1} تساوي {2} مرة متوسطها البالغ {3} خلال الفترات الـ {4} السابقة.",
    "{0} the amount recorded for this goal. Your balance is not affected.":
        "{0} المبلغ المسجل لهذا الهدف. رصيدك لا يتأثر.",
    "{0} The rest of Money Manager keeps working normally.":
        "{0} يواصل باقي Money Manager العمل بشكل طبيعي.",
    "{0} to go":
        "تبقى {0}",
    "{0} total − {1} {2}":
        "{0} إجمالاً − {1} {2}",
    "{0} transactions exported to {1}.":
        "تم تصدير {0} عمليات إلى {1}.",
    "{0} vs previous period":
        "{0} مقابل الفترة السابقة",
    "{0} You can open Money Manager without the lock and turn it off or set Windows Hello up again.":
        "{0} يمكنك فتح Money Manager دون القفل ثم إيقافه أو إعادة إعداد Windows Hello.",
    "{0} {1} compared with {2}{3}.":
        "{0} {1} مقارنة بـ {2}{3}.",
    "{0} · adjustment {1}":
        "{0} · تسوية {1}",
    "{0} · due today":
        "{0} · الموعد اليوم",
    "{0} · made on {1}":
        "{0} · أُعدّ في {1}",
    "{0} · month to date ({1})":
        "{0} · الشهر حتى اليوم ({1})",
    "{0} · overdue by {1} {2}":
        "{0} · متأخر بـ {1} {2}",
    "{0} · rising (no spending in the first half)":
        "{0} · مرتفعة (لا مصاريف في النصف الأول)",
    "{0} · stable (second half vs first half of the range)":
        "{0} · مستقرة (النصف الثاني مقابل الأول من الفترة)",
    "{0} · {1}\nNet worth: {2}\nBalance: {3}\nInvestments: {4}":
        "{0} · {1}\nصافي الثروة: {2}\nالرصيد: {3}\nالاستثمارات: {4}",
    "{0} · {1} a month":
        "{0} · {1} شهرياً",
    "{0} · {1} left · by {2}":
        "{0} · المتبقي {1} · قبل {2}",
    "{0} · {1} to Available":
        "{0} · {1} إلى المتاح",
    "{0} · {1} {2} (second half vs first half of the range)":
        "{0} · {1} {2} (النصف الثاني مقابل الأول من الفترة)",
    "{0} · {1} {2} left":
        "{0} · يتبقى {1} {2}",
    "{0}, month to date":
        "{0}، الشهر حتى اليوم",
    "{0}, year to date":
        "{0}، السنة حتى اليوم",
    "{0}: {1} of the monthly limit":
        "{0}: {1} من الحد الشهري",
    "{0}: {1} spent of {2}":
        "{0}: أُنفق {1} من {2}",
    "{0}: {1}, with no spending in the comparison period.":
        "{0}: {1}، دون مصاريف في فترة المقارنة.",
    "{0}: {1}; nothing recorded in the comparison period ({2}).":
        "{0}: {1}؛ لا شيء مسجل في فترة المقارنة ({2}).",
    "– Not enough data":
        "– بيانات غير كافية",
    "“{0}” goes to {1} from now on":
        "«{0}» يذهب إلى {1} من الآن فصاعداً",
    "“{0}” on {1} could not be recorded: {2}":
        "تعذّر تسجيل «{0}» في {1}: {2}",
    "‹ Previous":
        "‹ السابق",
    "● Fair":
        "● مقبول",
    "● In progress":
        "● جارٍ",
    "✓ Completed":
        "✓ مكتمل",
    "✓ Good":
        "✓ جيد",
    "✓ On track":
        "✓ في الموعد",
}
