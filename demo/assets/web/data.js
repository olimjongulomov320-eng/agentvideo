const FIRM = {
  name: "GSP LAW",
  fullName: "Gulyamov, Sadikov and Partners",
  phone1: "+998 95 109 52 25",
  phone2: "+998 88 771 44 33",
  phone3: "+998 97 425 87 70",
  email: "info@gsplaw.co.uz",
  address: { ru: "г. Ташкент, Мирабадский район, ул. Мирабад, дом 46а", uz: "Toshkent sh., Mirobod tumani, Mirobod ko'chasi, 46a-uy", en: "46a Mirobod St., Mirobod District, Tashkent" },
  telegram: "https://t.me/gsplawfirm",
  instagram: "https://www.instagram.com/gsplawuzb/",
  facebook: "https://www.facebook.com/legality.uz",
  youtube: "https://www.youtube.com/channel/UCp1ui0KzRWN4bPKLeBjCEmg",
  stats: [
    { num: "16+", label: "лет опыта" },
    { num: "$100M+", label: "портфель кейсов" },
    { num: "15", label: "адвокатов" },
    { num: "1000+", label: "клиентов" }
  ]
};

const SERVICES = [
  { icon: "⚖️", title: "Корпоративное право и M&A", desc: "Сопровождение сделок слияния и поглощения, корпоративное структурирование, акционерные соглашения" },
  { icon: "💻", title: "IT и киберправо", desc: "Правовое сопровождение IT-компаний, стартапов, защита персональных данных и кибербезопасность" },
  { icon: "🏦", title: "Банковское и финансовое право", desc: "Регуляторные вопросы, финтех, лицензирование, финансовые транзакции" },
  { icon: "📊", title: "Налоговая практика", desc: "Налоговое планирование, оптимизация, споры с налоговыми органами" },
  { icon: "🌐", title: "Экономические споры", desc: "Представление интересов в арбитражных судах, медиация, переговоры" },
  { icon: "📦", title: "Таможенное право", desc: "Сопровождение ВЭД, таможенное оформление, споры с таможенными органами" },
  { icon: "🛡️", title: "Уголовная защита бизнеса", desc: "Защита предпринимателей и руководителей в рамках уголовных дел" },
  { icon: "👥", title: "Трудовое право", desc: "Трудовые договоры, споры с работниками, кадровое делопроизводство" },
  { icon: "💡", title: "Интеллектуальная собственность", desc: "Регистрация товарных знаков, патентование, защита авторских прав" },
  { icon: "🤝", title: "Постоянное обслуживание", desc: "Комплексное юридическое сопровождение коммерческих организаций на постоянной основе" },
  { icon: "📝", title: "Контрактное право", desc: "Разработка и экспертиза договоров, переговоры, урегулирование разногласий" },
  { icon: "🏢", title: "Недвижимость", desc: "Сопровождение сделок с недвижимостью, девелоперские проекты, арендные споры" }
];

const LAWYERS = [
  {
    id: 1,
    slug: "sadikov-ruslan",
    photo: "photos/abdulloh-sodiq.jpeg",
    externalUrl: "https://olimjongulomov320-eng.github.io/Abdulloh_Sodiq/",
    name: "Sodiq Abdulloh G'ulom o'g'li",
    title: "Основатель, Управляющий партнёр",
    specialization: ["Экономические споры", "Корпоративное право", "M&A"],
    experience: "15+ лет",
    cases: "300+",
    initials: "СР",
    accentColor: "#1a2332",
    bio: { ru: "Управляющий партнёр GSP LAW. Специализируется на разрешении сложных экономических споров и сопровождении крупных M&A-сделок. Лично представлял интересы клиентов в судах всех инстанций.", uz: "GSP LAW boshqaruvchi sherigi. Murakkab iqtisodiy nizolarni hal etish va yirik M&A bitimlarini qo'llab-quvvatlashga ixtisoslashgan. Barcha instansiyalardagi sudlarda mijozlar manfaatlarini shaxsan himoya qilgan.", en: "Managing Partner of GSP LAW. Specializes in resolving complex economic disputes and supporting major M&A transactions. Has personally represented clients in courts at all levels." },
    description: { ru: "Руслан Гуламбаевич руководит стратегическим направлением фирмы и ведёт наиболее сложные дела в области корпоративного права. Под его руководством фирма сопроводила сделки на сумму более $100 млн.", uz: "U firmaning strategik yo'nalishini boshqaradi va korporativ huquq sohasidagi eng murakkab ishlarni olib boradi. Uning rahbarligi ostida firma $100 mln dan ortiq hajmdagi bitimlarni qo'llab-quvvatladi.", en: "He leads the firm's strategic direction and handles the most complex cases in corporate law. Under his leadership, the firm has supported transactions totaling over $100 million." },
    howIHelp: { ru: "Я специализируюсь на защите бизнеса в спорных и кризисных ситуациях — от арбитражных споров до враждебных поглощений. Помогаю структурировать бизнес так, чтобы минимизировать правовые риски.", uz: "Men biznesni nizoli va inqirozli vaziyatlarda himoya qilishga ixtisoslanganman — arbitraj nizolaridan to dushmanona qo'shib olishgacha. Huquqiy risklarni minimallashtirish uchun biznesni to'g'ri tuzilishiga yordam beraman.", en: "I specialize in protecting businesses in disputed and crisis situations — from arbitration to hostile takeovers. I help structure businesses to minimize legal risks." },
    services: {ru: ["Разрешение корпоративных споров", "Сопровождение сделок M&A", "Реструктуризация бизнеса", "Арбитражное производство", "Корпоративное управление", "Due Diligence"], uz: ["Korporativ nizolarni hal etish", "M&A bitimlarini qo'llab-quvvatlash", "Biznesni qayta tuzish", "Arbitraj ishi", "Korporativ boshqaruv", "Due Diligence"], en: ["Resolving corporate disputes", "M&A transaction support", "Business restructuring", "Arbitration proceedings", "Corporate governance", "Due Diligence"]},
    blog: [
      { title: "M&A в Узбекистане: тренды 2024", date: "10 ноября 2024", tag: "Рынок", excerpt: "Анализ рынка слияний и поглощений в Узбекистане и прогнозы на следующий год. Какие сектора наиболее активны..." },
      { title: "Корпоративные споры: как их предотвратить", date: "25 октября 2024", tag: "Советы", excerpt: "Практические советы по структурированию акционерных соглашений для избежания конфликтов между партнёрами..." },
      { title: "Due Diligence: полное руководство", date: "5 октября 2024", tag: "Руководство", excerpt: "Что нужно проверить перед покупкой бизнеса в Узбекистане. Чеклист из 50+ пунктов..." }
    ],
    education: [
      { degree: {ru: "Магистр права (LLM), Корпоративное право", uz: "Huquq magistri (LLM), Korporativ huquq", en: "Master of Laws (LLM), Corporate Law"}, institution: {ru: "London School of Economics, Великобритания", uz: "London Iqtisodiyot Maktabi, Buyuk Britaniya", en: "London School of Economics, United Kingdom"}, year: "2012" },
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2010" }
    ],
    achievements: {ru: ["Председатель комитета по корпоративному праву ТПП Узбекистана (2021–2024)", "Best M&A Lawyer Uzbekistan — Deal Makers Awards (2022)", "Сопровождение сделок общим объёмом свыше $100 млн", "Спикер Ташкентского международного инвестиционного форума (2021, 2022, 2023, 2024)"], uz: ["O'zbekiston TPPA korporativ huquq qo'mitasi raisi (2021–2024)", "Best M&A Lawyer Uzbekistan — Deal Makers Awards (2022)", "$100 mln dan ortiq hajmdagi bitimlarni qo'llab-quvvatlash", "Toshkent xalqaro investitsiya forumi spikeri (2021, 2022, 2023, 2024)"], en: ["Chairman of the Corporate Law Committee of the Chamber of Commerce of Uzbekistan (2021–2024)", "Best M&A Lawyer Uzbekistan — Deal Makers Awards (2022)", "Supported transactions totaling over $100 million", "Speaker at Tashkent International Investment Forum (2021, 2022, 2023, 2024)"]},
    publications: [
      { title: "M&A в развивающихся рынках Центральной Азии: тенденции и правовые барьеры", journal: "Корпоративное право и управление", year: "2024" },
      { title: "Корпоративное управление в Узбекистане: реформы и практика", journal: "Право и экономика", year: "2023" }
    ]
  },
  {
    id: 2,
    slug: "gulyamov-said",
    photo: "photos/gulyamov-said.jpeg",
    externalUrl: "https://gulyamov.org",
    name: { ru: "Гулямов Саид Саидахрарович", uz: "Gulyamov Said Saidaxrarovich", en: "Said Gulyamov" },
    title: "Основатель, Партнёр, Профессор",
    specialization: ["Киберправо", "IT-право", "Цифровое право"],
    experience: "20+ лет",
    cases: "200+",
    initials: "ГС",
    accentColor: "#c9a96e",
    bio: { ru: "Профессор и ведущий партнёр GSP LAW. Доктор юридических наук, признанный эксперт в области киберправа и цифрового законодательства Центральной Азии. Автор более 50 научных работ, регулярный докладчик на международных конференциях.", uz: "Doktor va GSP LAW yetakchi sherigi. Yuridik fanlar doktori, Markaziy Osiyo kiberhuquq va raqamli qonunchilik sohasida tan olingan ekspert. 50 dan ortiq ilmiy ishlar muallifi, xalqaro konferentsiyalarda muntazam ma'ruzachi.", en: "Professor and Leading Partner of GSP LAW. Doctor of Law, recognized expert in cyber law and digital legislation in Central Asia. Author of over 50 academic works, regular speaker at international conferences." },
    description: { ru: "Саид Саидахрарович — один из основателей фирмы и пионер в области IT-права в Узбекистане. Он консультирует государственные органы по вопросам цифрового законодательства и лично сопроводил более 200 проектов для ведущих IT-компаний региона.", uz: "Said Saidaxrarovich — firmaning asoschisi va O'zbekistonda IT-huquq sohasidagi kashshof. U raqamli qonunchilik masalalari bo'yicha davlat organlarini maslahat beradi va mintaqaning yetakchi IT-kompaniyalari uchun 200 dan ortiq loyihalarni shaxsan qo'llab-quvvatlagan.", en: "Said Saidakhrarovich is one of the firm's founders and a pioneer in IT law in Uzbekistan. He advises government bodies on digital legislation and has personally supported over 200 projects for leading IT companies in the region." },
    howIHelp: { ru: "Я помогаю IT-компаниям и стартапам выстраивать правовую архитектуру бизнеса с нуля, защищать интеллектуальную собственность и соответствовать требованиям регуляторов в сфере персональных данных.", uz: "Men IT-kompaniyalar va startaplarga noldan biznes huquqiy arxitekturasini qurishga, intellektual mulkni himoyalashga va shaxsiy ma'lumotlar sohasidagi regulyator talablariga javob berishga yordam beraman.", en: "I help IT companies and startups build legal architecture from scratch, protect intellectual property, and comply with data protection regulations." },
    services: {ru: ["Правовое регулирование IT-компаний", "Защита персональных данных", "Интеллектуальная собственность", "Киберпреступления", "Консультации по цифровому праву", "Лицензирование ПО"], uz: ["IT-kompaniyalarni huquqiy tartibga solish", "Shaxsiy ma'lumotlarni himoyalash", "Intellektual mulk", "Kiberjinoyatlar", "Raqamli huquq bo'yicha konsultatsiyalar", "Dasturiy ta'minotni litsenziyalash"], en: ["Legal regulation of IT companies", "Personal data protection", "Intellectual property", "Cybercrime", "Digital law consulting", "Software licensing"]},
    blog: [
      { title: "Киберправо в эпоху искусственного интеллекта", date: "15 октября 2024", tag: "Аналитика", excerpt: "Как новые технологии меняют правовую систему и что это означает для бизнеса в Узбекистане. Разбираем ключевые вопросы ответственности за действия ИИ-систем..." },
      { title: "Защита персональных данных: новые требования 2024", date: "3 сентября 2024", tag: "Законодательство", excerpt: "Обзор последних изменений в законодательстве о персональных данных и их влияние на IT-компании. Что нужно сделать прямо сейчас..." },
      { title: "IT-стартапы и правовые риски", date: "20 августа 2024", tag: "Стартапы", excerpt: "Топ-10 юридических ошибок, которые совершают стартапы на начальном этапе, и как их избежать. Практический чеклист..." }
    ],
    education: [
      { degree: {ru: "Доктор юридических наук", uz: "Yuridik fanlar doktori", en: "Doctor of Law"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2005" },
      { degree: {ru: "LLM, Информационное право", uz: "LLM, Axborot huquqi", en: "LLM, Information Law"}, institution: {ru: "Duke University School of Law, США", uz: "Duke University Huquq maktabi, AQSh", en: "Duke University School of Law, USA"}, year: "2003" },
      { degree: {ru: "Бакалавр права (с отличием)", uz: "Huquq bakalavri (faxriy)", en: "Bachelor of Laws (with honors)"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2000" }
    ],
    achievements: {ru: ["Профессор кафедры информационного права ТГЮУ (с 2010 г.)", "Советник по цифровому праву Министерства цифрового развития РУ (2020–2024)", "Legal Awards — «Лучший юрист в сфере IT-права», Центральная Азия (2023)", "Автор 3 монографий и более 50 научных статей по IT-праву и кибербезопасности"], uz: ["TDYU axborot huquqi kafedrasi professori (2010 yildan)", "O'zbekiston Raqamli rivojlanish vazirligi raqamli huquq bo'yicha maslahatchisi (2020–2024)", "Legal Awards — 'IT-huquq sohasidagi eng yaxshi yurist', Markaziy Osiyo (2023)", "IT-huquq va kiberxavfsizlik bo'yicha 3 ta monografiya va 50 dan ortiq ilmiy maqolalar muallifi"], en: ["Professor of Information Law at TSLU (since 2010)", "Advisor on Digital Law to the Ministry of Digital Development of Uzbekistan (2020–2024)", "Legal Awards — 'Best IT Law Lawyer', Central Asia (2023)", "Author of 3 monographs and over 50 academic articles on IT law and cybersecurity"]},
    publications: [
      { title: "Правовое регулирование систем искусственного интеллекта в странах СНГ", journal: "Право и цифровая экономика (ВАК)", year: "2024" },
      { title: "Кибербезопасность как объект правового регулирования в Центральной Азии", journal: "Журнал международного права", year: "2023" },
      { title: "Защита персональных данных в эпоху Big Data: сравнительно-правовой анализ", journal: "Государство и право (ВАК)", year: "2022" }
    ]
  },
  {
    id: 3,
    slug: "abraev-firuz",
    photo: "photos/abraev-firuz.jpeg",
    name: { ru: "Абраев Фируз Шавкатович", uz: "Abraev Firuz Shavkatovich", en: "Firuz Abraev" },
    title: "Партнёр, Специалист по контрактам",
    specialization: ["Контрактное право", "Банковское право", "ВЭД"],
    experience: "13+ лет",
    cases: "400+",
    initials: "АФ",
    accentColor: "#7b2d8b",
    bio: { ru: "Партнёр GSP LAW, ведущий эксперт по контрактному праву и внешнеэкономической деятельности. Разработал более 400 контрактов для крупных коммерческих организаций и международных компаний.", uz: "GSP LAW sherigi, shartnoma huquqi va tashqi iqtisodiy faoliyat bo'yicha yetakchi ekspert. Yirik tijorat tashkilotlari va xalqaro kompaniyalar uchun 400 dan ortiq shartnomalar ishlab chiqqan.", en: "Partner at GSP LAW, leading expert in contract law and foreign economic activity. Has drafted over 400 contracts for major commercial organizations and international companies." },
    description: { ru: "Фируз Шавкатович специализируется на разработке сложных коммерческих договоров и сопровождении ВЭД-сделок. Имеет глубокую экспертизу в банковском законодательстве Узбекистана.", uz: "Firuz Shavkatovich murakkab tijorat shartnomalari ishlab chiqish va tashqi savdo bitimlarini qo'llab-quvvatlashga ixtisoslashgan. O'zbekiston bank qonunchiligi sohasida chuqur tajribaga ega.", en: "Firuz Shavkatovich specializes in drafting complex commercial contracts and supporting foreign trade transactions. He has deep expertise in Uzbekistan's banking legislation." },
    howIHelp: { ru: "Создаю договоры, которые реально защищают ваши интересы, а не просто выглядят красиво. Анализирую риски в каждом пункте и помогаю вести переговоры с контрагентами.", uz: "Chiroyli ko'rinadigan emas, balki manfaatlaringizni haqiqatda himoya qiladigan shartnomalar tuzaman. Har bir bandda risklarni tahlil qilaman va kontragentlar bilan muzokaralarda yordam beraman.", en: "I draft contracts that genuinely protect your interests, not just look good. I analyze risks in every clause and help you negotiate with counterparties." },
    services: {ru: ["Разработка коммерческих договоров", "Экспертиза контрактов", "ВЭД-сделки", "Банковские гарантии", "Аккредитивы", "Переговоры с контрагентами"], uz: ["Tijorat shartnomalari ishlab chiqish", "Shartnomalar ekspertizasi", "Tashqi savdo bitishuvi", "Bank kafolatlari", "Akkreditivlar", "Kontragentlar bilan muzokaralar"], en: ["Drafting commercial contracts", "Contract review", "Foreign trade transactions", "Bank guarantees", "Letters of credit", "Counterparty negotiations"]},
    blog: [
      { title: "10 опасных пунктов в договорах, которые вы не замечаете", date: "5 ноября 2024", tag: "Контракты", excerpt: "Разбираем самые распространённые юридические ловушки в коммерческих договорах, которые обходятся бизнесу миллионами..." },
      { title: "ВЭД в 2024: что изменилось", date: "20 октября 2024", tag: "ВЭД", excerpt: "Обзор ключевых изменений в регулировании внешнеэкономической деятельности для узбекских компаний..." },
      { title: "Банковские гарантии как инструмент защиты бизнеса", date: "8 октября 2024", tag: "Банки", excerpt: "Когда и как использовать банковские гарантии для обеспечения обязательств в коммерческих сделках..." }
    ],
    education: [
      { degree: {ru: "LLM, Международное торговое право", uz: "LLM, Xalqaro savdo huquqi", en: "LLM, International Trade Law"}, institution: {ru: "Венский университет экономики и бизнеса, Австрия", uz: "Vena iqtisodiyot va biznes universiteti, Avstriya", en: "Vienna University of Economics and Business, Austria"}, year: "2014" },
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2011" }
    ],
    achievements: {ru: ["Сертифицированный специалист ICC по торговому финансированию (2016)", "Член Международной торговой палаты (ICC), комитет по банковским техникам (2018–н.в.)", "Разработал типовые контрактные формы для 3 крупных узбекских банков", "Победитель конкурса «Лучший корпоративный юрист» Ассоциации юристов Узбекистана (2021)"], uz: ["ICC savdo moliyalashtirish bo'yicha sertifikatlangan mutaxassis (2016)", "Xalqaro savdo palatasi (ICC) a'zosi, bank texnikasi qo'mitasi (2018–hozir)", "3 ta yirik o'zbek banki uchun standart shartnoma shakllarini ishlab chiqdi", "O'zbekiston Yuristlar assotsiatsiyasi 'Eng yaxshi korporativ yurist' tanlovining g'olibi (2021)"], en: ["ICC Certified Trade Finance Specialist (2016)", "Member of the International Chamber of Commerce (ICC), banking techniques committee (2018–present)", "Developed standard contract forms for 3 major Uzbek banks", "Winner of 'Best Corporate Lawyer' competition of the Bar Association of Uzbekistan (2021)"]},
    publications: [
      { title: "Регулирование ВЭД в Узбекистане: практика применения новых норм", journal: "Внешнеэкономическая деятельность", year: "2024" },
      { title: "Банковские гарантии в международных торговых сделках: сравнительный анализ", journal: "Банковское право (ВАК)", year: "2023" }
    ],
    certificates: [
      { title: { ru: "Адвокатское удостоверение (стр. 1)", uz: "Advokat guvohnomasi (1-bet)", en: "Bar Certificate (p. 1)" }, image: "certificates/certificates/Abrayev Firuz-1.png", file: "certificates/certificates/Abrayev Firuz.PDF" },
      { title: { ru: "Адвокатское удостоверение (стр. 2)", uz: "Advokat guvohnomasi (2-bet)", en: "Bar Certificate (p. 2)" }, image: "certificates/certificates/Abrayev Firuz-2.png", file: "certificates/certificates/Abrayev Firuz.PDF" }
    ]
  },
  {
    id: 4,
    slug: "khayitmurodov-ulugbek",
    photo: "photos/xaytmurodov-ulugbek.jpeg",
    phone: "+998 88 771 44 33",
    name: { ru: "Хайитмуродов Улугбек Отабекович", uz: "Xayitmurodov Ulugbek Otabekovich", en: "Ulugbek Xayitmurodov" },
    title: "Партнёр | Руководитель отдела корпоративного обслуживания",
    specialization: ["Корпоративное право", "Экономические споры", "Интеллектуальная собственность"],
    experience: "8+ лет",
    cases: "250+",
    initials: "ХУ",
    accentColor: "#2d6a4f",
    bio: { ru: "Партнёр GSP LAW и руководитель отдела постоянного юридического обслуживания корпоративных клиентов. 8 лет опыта в адвокатуре. Специализируется на экономических делах, бизнес-праве и интеллектуальной собственности. Кандидат юридических наук (PhD).", uz: "GSP LAW sherigi va korporativ mijozlarga doimiy yuridik xizmat ko'rsatish bo'limi boshlig'i. Advokatlik sohasida 8 yillik ish tajribasi. Iqtisodiy ishlar, biznes huquqi va intellektual mulk huquqi bo'yicha mutaxassis. Yuridik fanlar nomzodi (PhD).", en: "Partner at GSP LAW and Head of Permanent Legal Services for Corporate Clients. 8 years of experience in advocacy. Specializes in economic cases, business law and intellectual property. PhD in Law." },
    description: { ru: "Улугбек Хайитмуродов руководит отделом постоянного юридического сопровождения и ведёт сложные корпоративные дела для ключевых клиентов фирмы. Обладает академической базой Ташкентского государственного юридического университета на всех трёх уровнях образования (бакалавриат, магистратура, PhD) и глубокой экспертизой в экономических спорах и IP.", uz: "Ulug'bek Xayitmurodov doimiy yuridik qo'llab-quvvatlash bo'limini boshqaradi va firmaning asosiy mijozlari uchun murakkab korporativ ishlarni olib boradi. Toshkent davlat yuridik universitetida barcha uch ta'lim bosqichida (bakalavr, magistratura, PhD) akademik bazaga ega va iqtisodiy nizolar hamda IP sohasida chuqur tajribaga ega.", en: "Ulugbek Khayitmurodov heads the permanent legal support department and handles complex corporate cases for the firm's key clients. Has an academic foundation from Tashkent State University of Law at all three levels (bachelor's, master's, PhD) and deep expertise in economic disputes and IP." },
    howIHelp: { ru: "Обеспечиваю полное юридическое сопровождение бизнеса на постоянной основе — от ежедневных корпоративных вопросов до стратегических сделок. Специализируюсь на защите интеллектуальной собственности и ведении экономических споров.", uz: "Biznesni doimiy asosda to'liq yuridik qo'llab-quvvatlayman — kundalik korporativ masalalardan strategik bitimlargacha. Intellektual mulkni himoya qilish va iqtisodiy nizolarni yuritishga ixtisoslanganman.", en: "I provide full legal support to businesses on an ongoing basis — from daily corporate matters to strategic transactions. I specialize in intellectual property protection and handling economic disputes." },
    services: {ru: ["Постоянное юридическое сопровождение", "Экономические споры", "Бизнес-право", "Интеллектуальная собственность", "Корпоративные консультации", "Due Diligence"], uz: ["Doimiy yuridik qo'llab-quvvatlash", "Iqtisodiy nizolar", "Biznes huquqi", "Intellektual mulk", "Korporativ konsultatsiyalar", "Due Diligence"], en: ["Permanent legal support", "Economic disputes", "Business law", "Intellectual property", "Corporate consulting", "Due Diligence"]},
    blog: [
      { title: "ICSID и SCC как модели международного арбитража: уроки для Узбекистана", date: "Май 2025", tag: "Арбитраж", excerpt: "Статья исследует роль ICSID и SCC как механизмов международного арбитража и извлекает уроки для правовой системы Узбекистана. Опубликовано в International Law, Business and Political Science Journal (IF 13.24)." },
      { title: "Анализ правовых механизмов разрешения инвестиционных споров в Узбекистане", date: "2024", tag: "Инвестиции", excerpt: "Анализ правовых механизмов урегулирования инвестиционных споров в Узбекистане: проблемы и перспективы. Опубликовано в Miasto Przyszłości (Impact Factor 9.9)." },
      { title: "Цифровизация процедур разрешения инвестиционных споров", date: "2024", tag: "Цифровое право", excerpt: "От электронных доказательств до виртуальных заседаний — цифровая трансформация арбитражного процесса. Опубликовано в сборнике «Huquqiy tizimni raqamlashtirish»." }
    ],
    education: [
      { degree: {ru: "PhD (соискатель, кандидат юридических наук)", uz: "PhD (qo'shimcha mutaxassis, huquq fanlari nomzodi)", en: "PhD candidate in Law"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" },
      { degree: {ru: "Магистр права", uz: "Huquq magistri", en: "Master of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" },
      { degree: {ru: "Бакалавр права (частное право)", uz: "Huquq bakalavri (xususiy huquq)", en: "Bachelor of Laws (private law)"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" }
    ],
    achievements: {ru: ["8 лет опыта в адвокатуре", "Руководитель отдела постоянного юридического обслуживания корпоративных клиентов GSP LAW", "Соискатель учёной степени PhD, ТГЮУ", "ORCID: 0009-0002-3313-8340", "Участник VI Молодёжных образовательных чтений «Конституционализм», Уфа (2022)", "Сертификат публикации Miasto Przyszłości, Impact Factor 9.9 (2024)"], uz: ["Advokatlik sohasida 8 yillik ish tajribasi", "GSP LAW korporativ mijozlarga doimiy yuridik xizmat ko'rsatish bo'limi boshlig'i", "TDYU PhD unvoni izlovchisi", "ORCID: 0009-0002-3313-8340", "Konstitutsionalizm VI Yoshlar ta'lim o'qishlari ishtirokchisi, Ufa (2022)", "Miasto Przyszłości nashr sertifikati, Impact Factor 9.9 (2024)"], en: ["8 years of experience in advocacy", "Head of Permanent Legal Services for Corporate Clients at GSP LAW", "PhD candidate at TSLU", "ORCID: 0009-0002-3313-8340", "Participant of VI Youth Educational Readings 'Constitutionalism', Ufa (2022)", "Miasto Przyszłości publication certificate, Impact Factor 9.9 (2024)"]},
    publications: [
      { title: "ICSID and SCC as Models of International Arbitration: Lessons for the Legal System of Uzbekistan", journal: "International Law, Business and Political Science Journal (IF 13.24)", year: "2025", url: "https://doi.org/10.5281/zenodo.15511843" },
      { title: "Analysis of Legal Mechanisms for Resolving Investment Disputes in Uzbekistan: Problems and Prospects", journal: "Miasto Przyszłości, Vol. 51 (IF 9.9)", year: "2024", url: "https://inscience.uz/index.php/socinov/article/view/1947" },
      { title: "Международный опыт разрешения инвестиционных споров и его применение в Узбекистане", journal: "Academic Research in Modern Science", year: "2024", url: "https://doi.org/10.5281/zenodo.13884194" },
      { title: "Инвестиционные арбитражи и их значение для улучшения инвестиционного климата в Узбекистане", journal: "Development of Pedagogical Technologies in Modern Sciences", year: "2024", url: "https://doi.org/10.5281/zenodo.13922863" },
      { title: "Законодательные реформы Узбекистана в сфере инвестиций", journal: "International Scientific and Practical Conference", year: "2024", url: "https://www.openconference.us/index.php/civilization" },
      { title: "Инвестиционный климат Узбекистана и его влияние на развитие бизнеса", journal: "International Conference on Advance Science and Technology", year: "2024", url: "" },
      { title: "Цифровизация процедур разрешения инвестиционных споров: от электронных доказательств до виртуальных заседаний", journal: "Huquqiy tizimni raqamlashtirish — конференция ТГЮУ", year: "2024", url: "" },
      { title: "Concept, Essence and Principles of Islamic Investment Funds", journal: "Сборник научных трудов ТГЮУ (магистр)", year: "2022", url: "" },
      { title: "Закрепление в Конституции Узбекистана института прав и свобод гражданина", journal: "VI Молодёжные образовательные чтения, Уфа", year: "2022", url: "" }
    ],
    certificates: [
      { title: { ru: "Удостоверение адвоката", uz: "Advokat guvohnomasi", en: "Bar Certificate" }, image: "certificates/certificates/Khayitmurodov Ulugbek Otabekovich.jpg", file: "certificates/certificates/Khayitmurodov Ulugbek Otabekovich.jpg" },
      { title: { ru: "Сертификат публикации Miasto Przyszłości (IF 9.9)", uz: "Miasto Przyszłości nashr sertifikati (IF 9.9)", en: "Miasto Przyszłości Publication Certificate (IF 9.9)" }, image: "certificates/certificates/Хайитмуродов_Улугбек_Отабекович_UK_SERT-1.png", file: "certificates/certificates/Хайитмуродов_Улугбек_Отабекович_UK_SERT.pdf" },
      { title: { ru: "Научная публикация (стр. 1)", uz: "Ilmiy nashr (1-bet)", en: "Academic Publication (p. 1)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-1.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" },
      { title: { ru: "Научная публикация (стр. 2)", uz: "Ilmiy nashr (2-bet)", en: "Academic Publication (p. 2)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-2.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" },
      { title: { ru: "Научная публикация (стр. 3)", uz: "Ilmiy nashr (3-bet)", en: "Academic Publication (p. 3)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-3.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" },
      { title: { ru: "Научная публикация (стр. 4)", uz: "Ilmiy nashr (4-bet)", en: "Academic Publication (p. 4)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-4.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" },
      { title: { ru: "Научная публикация (стр. 5)", uz: "Ilmiy nashr (5-bet)", en: "Academic Publication (p. 5)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-5.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" },
      { title: { ru: "Научная публикация (стр. 6)", uz: "Ilmiy nashr (6-bet)", en: "Academic Publication (p. 6)" }, image: "certificates/certificates/Хайитмуродов Улугбек  124-129-6.png", file: "certificates/certificates/Хайитмуродов Улугбек  124-129.pdf" }
    ]
  },
  {
    id: 5,
    slug: "mikhilyev-saidulla",
    photo: "photos/mikhilyev-saidulla.jpeg",
    name: { ru: "Михилиев Саидулла", uz: "Mixliyev Saidulla", en: "Saidulla Mikhilyev" },
    title: "Адвокат",
    specialization: ["Гражданское право", "Административное право", "Экономические споры"],
    experience: "15+ лет",
    cases: "200+",
    initials: "МС",
    accentColor: "#17435a",
    bio: { ru: "Адвокат с более чем 15-летним опытом руководства и судебной работы. Специализируется на гражданских, экономических и административных делах. Бывший председатель суда и судья в ряде судов Ташкента и Сурхандарьинской области — смотрит на каждое дело «взглядом судьи».", uz: "15 yildan ortiq rahbarlik va sudyalik tajribasiga ega advokat. Fuqarolik, iqtisodiy va ma'muriy ishlarga ixtisoslashgan. Sobiq sud raisi va Toshkent hamda Surxondaryo sudlarida sudya — har bir ishga \"sudya nigohi\" bilan qaraydi.", en: "Advocate with over 15 years of leadership and judicial experience. Specializes in civil, economic and administrative cases. Former court chairman and judge in several Tashkent and Surkhandarya courts — views every case through the 'judge's eye'." },
    description: { ru: "Саидулла Михилиев — бывший председатель Бектемирского районного административного суда и судья экономических, гражданских и административных судов Ташкента и Сурхандарьи (2017–2020 и ранее). Имеет академическое образование в ТГЮУ (бакалавриат) и Университете мировой экономики и дипломатии (магистратура). Свободно владеет узбекским, русским и английским языками. С марта 2024 года — адвокат GSP LAW.", uz: "Mixliyev Saidulla — Bektemir tumanlararo ma'muriy sudining sobiq raisi va Toshkent hamda Surxondaryo iqtisodiy, fuqarolik va ma'muriy sudlarida sudya (2017–2020 va undan avval). TDYU (bakalavr) va Jahon iqtisodiyoti va diplomatiya universiteti (magistratura) da akademik ta'lim olgan. O'zbek, rus va ingliz tillarini erkin biladi. 2024-yil mart oyidan GSP LAW advokati.", en: "Saidulla Mikhilyev is a former chairman of Bektemir District Administrative Court and judge in economic, civil and administrative courts of Tashkent and Surkhandarya (2017–2020 and earlier). Has academic education at TSLU (bachelor's) and University of World Economy and Diplomacy (master's). Fluent in Uzbek, Russian and English. Since March 2024 — advocate at GSP LAW." },
    howIHelp: { ru: "Используя многолетний опыт судебной работы на всех уровнях, строю сильную позицию клиента в гражданских, экономических и административных делах. Вижу дело так, как его видит судья — это ключевое преимущество при выработке стратегии.", uz: "Barcha darajalardagi sud ishidagi ko'p yillik tajribadan foydalanib, fuqarolik, iqtisodiy va ma'muriy ishlarda mijozning kuchli pozitsiyasini quraman. Ishni sudya ko'zi bilan ko'raman — bu strategiya ishlab chiqishda asosiy ustunlik.", en: "Using years of judicial experience at all levels, I build a strong position for clients in civil, economic and administrative cases. I see the case as a judge does — this is the key advantage when developing strategy." },
    services: {ru: ["Гражданские споры", "Экономические дела", "Административное право", "Судебное представительство", "Апелляция и кассация", "Правовая экспертиза"], uz: ["Fuqarolik nizolari", "Iqtisodiy ishlar", "Ma'muriy huquq", "Sudda ifodalash", "Apellyatsiya va kassatsiya", "Huquqiy ekspertiza"], en: ["Civil disputes", "Economic cases", "Administrative law", "Court representation", "Appeal and cassation", "Legal expertise"]},
    blog: [
      { title: "Как работает судебная система Узбекистана изнутри", date: "10 ноября 2024", tag: "Аналитика", excerpt: "Взгляд изнутри на процедуры и практику узбекских судов..." },
      { title: "Административные споры: стратегии защиты", date: "25 октября 2024", tag: "Советы", excerpt: "Ключевые ошибки при оспаривании административных решений и как их избежать..." }
    ],
    education: [
      { degree: {ru: "Магистр права", uz: "Huquq magistri", en: "Master of Laws"}, institution: {ru: "Университет мировой экономики и дипломатии", uz: "Jahon iqtisodiyoti va diplomatiya universiteti", en: "University of World Economy and Diplomacy"}, year: "2007" },
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2005" }
    ],
    achievements: {ru: ["Председатель Бектемирского районного административного суда г. Ташкента (2017–2020)", "Судья Ташкентского городского экономического суда, Мирабадского межрайонного гражданского суда, Ташкентского межрайонного административного суда", "Судья Кумкурганского межрайонного гражданского суда, Сурхандарья", "Свободное владение узбекским, русским и английским языками"], uz: ["Toshkent sh. Bektemir tumanlararo ma'muriy sudi raisi (2017–2020)", "Toshkent shahar iqtisodiy sudi, Mirobod tumanlararo fuqarolik sudi, Toshkent tumanlararo ma'muriy sudida sudya", "Qumqo'rg'on tumanlararo fuqarolik sudi, Surxondaryo viloyatida sudya", "O'zbek, rus va ingliz tillarini erkin bilish"], en: ["Chairman of Bektemir District Administrative Court of Tashkent (2017–2020)", "Judge at Tashkent City Economic Court, Mirabad Inter-District Civil Court, Tashkent Inter-District Administrative Court", "Judge at Kumkurgan Inter-District Civil Court, Surkhandarya", "Fluent in Uzbek, Russian and English"]},
    publications: [],
    certificates: [
      { title: { ru: "Удостоверение (стр. 1)", uz: "Guvohnoma (1-bet)", en: "Certificate (p. 1)" }, image: "certificates/certificates/Saidulla Mixliyev-1.png", file: "certificates/certificates/Saidulla Mixliyev.PDF" },
      { title: { ru: "Удостоверение (стр. 2)", uz: "Guvohnoma (2-bet)", en: "Certificate (p. 2)" }, image: "certificates/certificates/Saidulla Mixliyev-2.png", file: "certificates/certificates/Saidulla Mixliyev.PDF" },
      { title: { ru: "Удостоверение (стр. 3)", uz: "Guvohnoma (3-bet)", en: "Certificate (p. 3)" }, image: "certificates/certificates/Saidulla Mixliyev-3.png", file: "certificates/certificates/Saidulla Mixliyev.PDF" },
      { title: { ru: "Удостоверение (стр. 4)", uz: "Guvohnoma (4-bet)", en: "Certificate (p. 4)" }, image: "certificates/certificates/Saidulla Mixliyev-4.png", file: "certificates/certificates/Saidulla Mixliyev.PDF" }
    ]
  },
  {
    id: 6,
    slug: "isamutdinov-ulugbek",
    photo: "photos/isamutdinov-ulugbek.jpeg",
    name: { ru: "Исамутдинов Улугбек", uz: "Isamutdinov Ulugbek", en: "Ulugbek Isamutdinov" },
    title: "Финансовый юрист | Аудитор",
    specialization: ["Налоговое право", "Финансовые споры", "Бухгалтерский учёт и аудит"],
    experience: "10+ лет",
    cases: "150+",
    initials: "ИУ",
    accentColor: "#c9a96e",
    bio: { ru: "Высококвалифицированный финансист и эксперт в области бухгалтерского учёта, финансов и налоговых споров. Помогает бизнесу защититься от налоговых рисков, выстроить законную и эффективную финансовую систему и разрешить сложные экономические споры.", uz: "Ko'p yillik amaliy tajribaga ega yuqori malakali moliyachi, buxgalteriya hisobi, moliya va soliq nizolari bo'yicha yetuk ekspert. Biznesni soliq xavflaridan himoya qilish, moliyaviy tizimni qonuniy va samarali shakllantirish hamda murakkab iqtisodiy nizolarni yechishda professional ko'mak beradi.", en: "Highly qualified financial specialist and expert in accounting, finance and tax disputes. Helps businesses protect against tax risks, build a legal and effective financial system and resolve complex economic disputes." },
    description: { ru: "Улугбек Исамутдинов — эксперт на стыке финансов и права. Специализируется на защите предпринимателей в налоговых спорах, финансовом и налоговом аудите, постановке бухгалтерского учёта по международным стандартам (МСФО/НСБУ), а также на финансовом консалтинге для повышения рентабельности бизнеса.", uz: "Isamutdinov Ulug'bek — moliya va huquq kesishmasidagi ekspert. Tadbirkorlarni soliq nizolarida himoya qilish, moliyaviy va soliq auditi, xalqaro standartlar (BHMS/MHXS) asosida buxgalteriya tizimini yo'lga qo'yish va biznes rentabelligini oshirish bo'yicha moliyaviy konsaltingga ixtisoslashgan.", en: "Isamutdinov Ulugbek is an expert at the intersection of finance and law. Specializes in protecting entrepreneurs in tax disputes, financial and tax auditing, accounting setup according to international standards (IFRS/NSBU), and financial consulting to increase business profitability." },
    howIHelp: { ru: "Защищаю бизнес от налоговых доначислений, провожу финансовый аудит для выявления скрытых рисков, настраиваю бухгалтерский учёт с нуля по МСФО и консультирую по оптимизации финансовых потоков.", uz: "Biznesni soliq qo'shimcha hisob-kitoblaridan himoya qilaman, yashirin xavflarni aniqlash uchun moliyaviy audit o'tkazaman, BHMS bo'yicha buxgalteriya tizimini noldan sozlayman va moliyaviy oqimlarni optimallashtirish bo'yicha maslahat beraman.", en: "I protect businesses from additional tax assessments, conduct financial audits to identify hidden risks, set up accounting from scratch according to IFRS and advise on optimizing financial flows." },
    services: {ru: ["Налоговые споры", "Финансовый аудит", "Бухгалтерский учёт (МСФО)", "Налоговое планирование", "Финансовый консалтинг", "Комплаенс"], uz: ["Soliq nizolari", "Moliyaviy audit", "Buxgalteriya hisobi (BHMS)", "Soliq rejalashtirish", "Moliyaviy konsalting", "Komplaens"], en: ["Tax disputes", "Financial audit", "Accounting (IFRS)", "Tax planning", "Financial consulting", "Compliance"]},
    blog: [
      { title: "Налоговые споры в Узбекистане: как выиграть", date: "8 ноября 2024", tag: "Налоги", excerpt: "Практические советы по успешному оспариванию налоговых доначислений..." },
      { title: "Внутренний аудит как инструмент защиты бизнеса", date: "22 октября 2024", tag: "Аудит", excerpt: "Почему регулярный внутренний аудит снижает налоговые риски компании..." }
    ],
    education: [
      { degree: {ru: "Магистр финансового права", uz: "Moliya huquqi magistri", en: "Master of Financial Law"}, institution: {ru: "Ташкентский финансовый институт", uz: "Toshkent moliya instituti", en: "Tashkent Financial Institute"}, year: "2014" },
      { degree: {ru: "Сертифицированный аудитор (CIA)", uz: "Sertifikatlangan auditor (CIA)", en: "Certified Internal Auditor (CIA)"}, institution: {ru: "Institute of Internal Auditors", uz: "Ichki auditorlar instituti", en: "Institute of Internal Auditors"}, year: "2016" }
    ],
    achievements: {ru: ["Успешное оспаривание налоговых доначислений на сумму свыше $3 млн", "Разработал систему внутреннего аудита для 20+ компаний", "Эксперт по финансовому праву Торгово-промышленной палаты Узбекистана"], uz: ["$3 mln dan ortiq soliq qo'shimchalarini muvaffaqiyatli ixtilof qilish", "20 dan ortiq kompaniya uchun ichki audit tizimini ishlab chiqdi", "O'zbekiston Savdo-sanoat palatasi moliya huquqi bo'yicha ekspert"], en: ["Successfully challenged additional tax assessments totaling over $3 million", "Developed an internal audit system for 20+ companies", "Expert in financial law of the Chamber of Commerce of Uzbekistan"]},
    publications: [
      { title: "Налоговые споры в условиях цифровизации: новые подходы", journal: "Финансы и налоги", year: "2024" },
      { title: "Внутренний аудит как инструмент минимизации правовых рисков", journal: "Бухгалтерский учёт и аудит", year: "2023" }
    ],
    certificates: [
      { title: { ru: "Адвокатское удостоверение", uz: "Advokat guvohnomasi", en: "Bar Certificate" }, image: "certificates/certificates/Ulug'bek Isamuddinov-1.png", file: "certificates/certificates/Ulug'bek Isamuddinov.PDF" }
    ]
  },
  {
    id: 7,
    slug: "sardor",
    photo: "photos/sardor.jpeg",
    name: "Sardor Abduxamidov",
    title: "Юрист",
    specialization: ["Уголовное право", "Киберпреступления", "Корпоративное право"],
    experience: "3+ лет",
    cases: "30+",
    initials: "SA",
    accentColor: "#17435a",
    bio: { ru: "Юрист GSP LAW, специализирующийся на уголовном праве и киберпреступлениях. Обеспечивает защиту клиентов на стадии тergova и в суде, особенно по делам, связанным с электронными доказательствами и цифровыми технологиями.", uz: "GSP LAW yurist, jinoyat huquqi va kiberjinoyatlar bo'yicha ixtisoslashgan. Tergov va sud bosqichida, ayniqsa elektron dalillar va raqamli texnologiyalar bilan bog'liq ishlarda mijozlarni himoya qiladi.", en: "Lawyer at GSP LAW specializing in criminal law and cybercrime. Provides client defense at the investigation and court stages, especially in cases involving electronic evidence and digital technologies." },
    description: { ru: "Сардор Абдухамидов специализируется на уголовном праве с акцентом на киберпреступления — анализ электронных доказательств, цифровая криминалистика, защита в делах, связанных с Telegram, WhatsApp и международной юрисдикцией. Также обслуживает IT-компании и стартапы по корпоративным вопросам: контракты, due diligence, трудовые отношения и защита интеллектуальной собственности.", uz: "Sardor Abduxamidov jinoyat huquqi, ayniqsa kiberjinoyatlar bo'yicha ixtisoslashgan — elektron dalillarni tahlil qilish, raqamli ekspertiza, Telegram, WhatsApp va xalqaro yurisdiktsiya bilan bog'liq ishlarda himoya. Shuningdek, IT-kompaniyalar va startaplarga korporativ masalalarda xizmat ko'rsatadi.", en: "Sardor Abduxamidov specializes in criminal law with a focus on cybercrime — electronic evidence analysis, digital forensics, defense in cases involving Telegram, WhatsApp and international jurisdiction. Also serves IT companies and startups on corporate matters." },
    howIHelp: { ru: "Помогаю клиентам в уголовных делах по киберпреступлениям: анализирую цифровые доказательства, выстраиваю стратегию защиты на следствии и в суде. IT-компаниям помогаю с контрактами, IP и правовой структурой бизнеса.", uz: "Kiberjinoyatlar bo'yicha jinoyat ishlarida mijozlarga yordam beraman: raqamli dalillarni tahlil qilaman, tergov va sudda himoya strategiyasini quraman. IT-kompaniyalarga shartnomalar, IP va biznesning huquqiy tuzilmasida yordam beraman.", en: "I help clients in criminal cybercrime cases: analyze digital evidence, build defense strategies at investigation and court stages. I help IT companies with contracts, IP and business legal structure." },
    services: {ru: ["Уголовная защита", "Киберпреступления", "Электронные доказательства", "IT-компании", "Корпоративные договоры", "Интеллектуальная собственность"], uz: ["Jinoiy himoya", "Kiberjinoyatlar", "Elektron dalillar", "IT-kompaniyalar", "Korporativ shartnomalar", "Intellektual mulk"], en: ["Criminal defense", "Cybercrime", "Electronic evidence", "IT companies", "Corporate contracts", "Intellectual property"]},
    blog: [], education: [
      { degree: {ru: "Магистр права", uz: "Huquq magistri", en: "Master of Laws"}, institution: {ru: "Академия правоохранительных органов Республики Узбекистан", uz: "O'zbekiston Respublikasi huquq-tartibot organlari akademiyasi", en: "Academy of Law Enforcement Agencies of the Republic of Uzbekistan"}, year: "2022" },
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2020" }
    ], achievements: {ru: ["Специализация в цифровой криминалистике и анализе электронных доказательств", "Опыт защиты в делах с международной юрисдикцией и мессенджерами", "Юридическое сопровождение IT-компаний и стартапов"], uz: ["Raqamli ekspertiza va elektron dalillarni tahlil qilish bo'yicha ixtisoslashuv", "Xalqaro yurisdiktsiya va messenjerlar bilan bog'liq ishlarda himoya tajribasi", "IT-kompaniyalar va startaplarga yuridik xizmat ko'rsatish"], en: ["Specialization in digital forensics and electronic evidence analysis", "Defense experience in cases with international jurisdiction and messengers", "Legal support for IT companies and startups"]}, publications: []
  },
  {
    id: 8,
    slug: "alijonova-daria",
    photo: "photos/alijonova-daria.jpeg",
    name: { ru: "Алижонова Дарья", uz: "Alijonova Darya", en: "Darya Alijonova" },
    title: "Адвокат | Международный юрист",
    specialization: ["Уголовное право", "Киберправо", "Космическое право"],
    experience: "11+ лет",
    cases: "100+",
    initials: "АД",
    accentColor: "#2d4a7a",
    bio: { ru: "Высококвалифицированный адвокат и международный юрист с более чем 11-летним опытом. Сочетает экспертизу в уголовном праве с передовыми знаниями в области цифровых технологий, кибербезопасности и космического права. Одна из немногих юристов в Центральной Азии, специализирующихся на космическом праве.", uz: "11 yildan ortiq tajribaga ega yuqori malakali advokat va xalqaro yurist. Jinoyat huquqi sohasidagi bilimlarini raqamli texnologiyalar, kiberxavfsizlik va kosmik huquq bo'yicha ilg'or bilimlar bilan uyg'unlashtiradi. Markaziy Osiyoda kosmik huquq bo'yicha ixtisoslashgan kamdan-kam yuristlardan biri.", en: "Highly accomplished advocate and international lawyer with over 11 years of experience. Combines expertise in criminal law with cutting-edge knowledge in cybersecurity, digital law and space law. One of the few lawyers in Central Asia specializing in space law." },
    description: { ru: "Дарья Алижонова начала карьеру в судебной системе, занимая должности в сфере уголовного судопроизводства. Сегодня она — признанный международный юрист, объединяющий тюркоязычные государства в своей практике и выстраивающий правовые мосты между Узбекистаном и зарубежными юрисдикциями. Консультирует иностранные государственные органы и частные компании по вопросам кибербезопасности и защиты данных.", uz: "Dariya Alijonova karerini sud tizimida jinoyat sudlovida boshlagan. Bugun u — o'z amaliyotida turkiy davlatlarni birlashtiruvchi va O'zbekiston bilan xorijiy yurisdiktsiyalar o'rtasida huquqiy ko'priklar qurayotgan tan olingan xalqaro yurist. Xorijiy davlat idoralari va xususiy kompaniyalarga kiberxavfsizlik va ma'lumotlarni himoya qilish bo'yicha konsultatsiya beradi.", en: "Daria Alijonova began her career in the judicial system in criminal proceedings. Today she is a recognised international lawyer uniting Turkic-speaking nations in her practice and building legal bridges between Uzbekistan and foreign jurisdictions. She advises foreign government institutions and private companies on cybersecurity and data protection." },
    howIHelp: { ru: "Помогаю в уголовных делах, защищаю права клиентов в цифровой среде и консультирую по международному праву. Моя специализация на стыке традиционного права и новых технологий — от киберпреступлений до правового регулирования космических технологий.", uz: "Jinoyat ishlarida yordam beraman, raqamli muhitda mijozlar huquqlarini himoya qilaman va xalqaro huquq bo'yicha maslahat beraman. Mening ixtisosligim an'anaviy huquq va yangi texnologiyalar kesishmasida — kiberjinoyatlardan tortib kosmik texnologiyalarni huquqiy tartibga solishgacha.", en: "I assist in criminal cases, protect clients' rights in the digital environment and advise on international law. My specialization is at the intersection of traditional law and new technologies — from cybercrime to legal regulation of space technologies." },
    services: {ru: ["Уголовная защита", "Киберправо", "Цифровое право", "Международное право", "Космическое право", "Кибербезопасность"], uz: ["Jinoiy himoya", "Kiberhuquq", "Raqamli huquq", "Xalqaro huquq", "Kosmik huquq", "Kiberxavfsizlik"], en: ["Criminal defense", "Cyber law", "Digital law", "International law", "Space law", "Cybersecurity"]},
    blog: [], education: [
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2013" }
    ], achievements: {ru: ["11+ лет опыта в уголовном и международном праве", "Один из немногих специалистов по космическому праву в Центральной Азии", "Консультант иностранных государственных органов по кибербезопасности", "Международная практика в тюркоязычных государствах"], uz: ["Jinoiy va xalqaro huquq sohasida 11+ yillik tajriba", "Markaziy Osiyoda kosmik huquq bo'yicha ixtisoslashgan kamdan-kam mutaxassislardan biri", "Kiberxavfsizlik bo'yicha xorijiy davlat organlarining maslahatchisi", "Turkiy davlatlarda xalqaro amaliyot"], en: ["11+ years experience in criminal and international law", "One of the few specialists in space law in Central Asia", "Consultant of foreign government bodies on cybersecurity", "International practice in Turkic-speaking states"]}, publications: []
  },
  {
    id: 9,
    slug: "boytrayev-dilshod",
    photo: "photos/boytrayev-dilshod.jpeg",
    name: "Boyturayev Dilshod",
    title: "Адвокат",
    specialization: ["Уголовное право", "Экономические споры", "Корпоративное право"],
    experience: "6+ лет",
    cases: "70+",
    initials: "БД",
    accentColor: "#1a4a6e",
    bio: { ru: "Адвокат с многолетним практическим опытом, ранее работавший в органах прокуратуры и руководивший юридической службой крупных компаний. Глубокая экспертиза в уголовном, экономическом и корпоративном праве.", uz: "Ko'p yillik amaliy tajribaga ega advokat, prokuratura organlarida va yirik kompaniyalarning yuridik xizmati boshlig'i sifatida faoliyat yuritgan. Jinoyat, iqtisodiy va korporativ huquqda chuqur tajriba.", en: "Lawyer with years of practical experience, formerly worked in the prosecutor's office and headed the legal service of major companies. Deep expertise in criminal, economic and corporate law." },
    description: { ru: "Дилшод Бойтураев прошёл путь от следователя прокуратуры до государственного обвинителя, достигнув должности прокурора отдела надзора Джизакской областной прокуратуры. Сегодня в качестве адвоката защищает интересы предпринимателей и физических лиц в экономических, корпоративных и уголовных делах. Знание системы изнутри позволяет ему выстраивать наиболее эффективные стратегии защиты.", uz: "Dilshod Boyturayev tergov xodimidan davlat ayblovchisiga qadar, Jizzax viloyati prokuraturasida nazorat bo'limi prokurori lavozimigacha ko'tarilgan. Bugun advokat sifatida tadbirkorlar va jismoniy shaxslarning iqtisodiy, korporativ va jinoyat ishlarida manfaatlarini himoya qiladi.", en: "Dilshod Boyturayev rose from prosecutor's investigator to state prosecutor, reaching the position of supervising prosecutor at Jizzax regional prosecutor's office. Today as an advocate he defends interests of entrepreneurs and individuals in economic, corporate and criminal cases." },
    howIHelp: { ru: "Используя многолетний опыт в прокуратуре, помогаю клиентам выстраивать сильную защитную позицию в уголовных и экономических делах, сопровождаю бизнес в корпоративных спорах и договорных отношениях.", uz: "Prokuraturadagi ko'p yillik tajribadan foydalanib, mijozlarga jinoyat va iqtisodiy ishlarda kuchli himoya pozitsiyasini qurishga yordam beraman, biznesni korporativ nizo va shartnoma munosabatlarida qo'llab-quvvatlayman.", en: "Using years of experience in the prosecutor's office, I help clients build a strong defense position in criminal and economic cases, and support businesses in corporate disputes and contractual relations." },
    services: {ru: ["Уголовная защита", "Экономические споры", "Корпоративные вопросы", "Судебное представительство", "Договорное право"], uz: ["Jinoiy himoya", "Iqtisodiy nizolar", "Korporativ masalalar", "Sudda ifodalash", "Shartnoma huquqi"], en: ["Criminal defense", "Economic disputes", "Corporate matters", "Court representation", "Contract law"]},
    blog: [], education: [
      { degree: {ru: "Юридическое образование", uz: "Yuridik ta'lim", en: "Legal Education"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" }
    ], achievements: {ru: ["Прокурор отдела надзора за исполнением законодательства в экономической сфере, Джизакская областная прокуратура", "Государственный обвинитель по уголовным делам", "Следователь прокуратуры с опытом расследования сложных уголовных дел", "Научно-практическая деятельность по корпоративному праву и предпринимательству"], uz: ["Jizzax viloyati prokuraturasida iqtisodiy sohada qonunchilik ijrosini nazorat qilish bo'limi prokurori", "Jinoiy ishlar bo'yicha davlat ayblovchisi", "Murakkab jinoiy ishlarni tergov qilish tajribasiga ega prokuratura tergovchisi", "Korporativ huquq va tadbirkorlik bo'yicha ilmiy-amaliy faoliyat"], en: ["Prosecutor of the department for supervision of legislation in the economic sphere, Jizzax regional prosecutor's office", "State prosecutor in criminal cases", "Investigator with experience in complex criminal cases", "Research and practical activities in corporate law and entrepreneurship"]}, publications: []
  },
  {
    id: 10,
    slug: "ergasheva-sevinch",
    photo: "photos/ergasheva-sevinch.jpeg",
    name: { ru: "Эргашева Севинч", uz: "Ergasheva Sevinch", en: "Sevinch Ergasheva" },
    title: "Адвокат",
    specialization: ["Корпоративное право", "Экономические споры", "Гражданское право"],
    experience: "4+ лет",
    cases: "50+",
    initials: "ЭС",
    accentColor: "#3a5c8a",
    bio: { ru: "Адвокат GSP LAW, специализирующаяся на корпоративном праве, экономических и гражданских спорах. Завершает магистратуру Ташкентского государственного юридического университета. Отличается стратегическим подходом и нацеленностью на результат.", uz: "GSP LAW advokati, korporativ huquq, iqtisodiy va fuqarolik nizolariga ixtisoslashgan. Toshkent davlat yuridik universitetining magistratura bosqichini yakunlamoqda. Strategik yondashuv va natijaga yo'nalganligi bilan ajralib turadi.", en: "Advocate at GSP LAW specializing in corporate law, economic and civil disputes. Completing a Master's degree at Tashkent State University of Law. Stands out for strategic thinking and results-oriented approach." },
    description: { ru: "Севинч Эргашева занимается полным сопровождением корпоративных процедур — от создания компаний до разрешения споров между акционерами. В экономических делах профессионально защищает интересы предпринимателей в судах. В гражданских делах ведёт широкий спектр споров: имущество, наследство, долги, трудовые и семейные дела.", uz: "Sevinch Ergasheva korporativ protseduralarni to'liq qo'llab-quvvatlaydi — kompaniyalar ta'sisidan aksiyadorlar o'rtasidagi nizolarni hal etishgacha. Iqtisodiy ishlarda iqtisodiy sudlarda tadbirkorlar manfaatlarini professional himoya qiladi. Fuqarolik ishlarida mulk, meros, qarz, mehnat va oilaviy nizolarning keng doirasini olib boradi.", en: "Sevinch Ergasheva provides full support of corporate procedures — from company incorporation to resolving shareholder disputes. In economic cases, she professionally defends entrepreneurs' interests in courts. In civil cases, she handles a wide range of disputes: property, inheritance, debts, labor and family matters." },
    howIHelp: { ru: "Помогаю бизнесу решать корпоративные и экономические вопросы — от учредительных документов до судебных споров. Частным лицам — в гражданских делах любой сложности: имущество, семья, долги, трудовые конфликты.", uz: "Biznesga korporativ va iqtisodiy masalalarni hal etishda yordam beraman — ta'sis hujjatlaridan sud nizolarigacha. Jismoniy shaxslarga — har qanday murakkablikdagi fuqarolik ishlarida: mulk, oila, qarz, mehnat nizolari.", en: "I help businesses resolve corporate and economic issues — from founding documents to court disputes. For individuals — in civil cases of any complexity: property, family, debts, labor conflicts." },
    services: {ru: ["Корпоративное право", "Экономические споры", "Гражданские дела", "Учредительные документы", "Имущественные споры", "Семейное право"], uz: ["Korporativ huquq", "Iqtisodiy nizolar", "Fuqarolik ishlari", "Ta'sis hujjatlari", "Mulkiy nizolar", "Oila huquqi"], en: ["Corporate law", "Economic disputes", "Civil cases", "Founding documents", "Property disputes", "Family law"]},
    blog: [], education: [
      { degree: {ru: "Магистратура (в процессе)", uz: "Magistratura (jarayonda)", en: "Master's degree (in progress)"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2025" },
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2023" }
    ], achievements: {ru: ["Стратегический подход к ведению корпоративных и экономических дел", "Опыт в гражданских делах: имущество, наследство, семейное право", "Полное сопровождение корпоративных процедур"], uz: ["Korporativ va iqtisodiy ishlarga strategik yondashuv", "Fuqarolik ishlarida tajriba: mulk, meros, oila huquqi", "Korporativ protseduralarni to'liq qo'llab-quvvatlash"], en: ["Strategic approach to corporate and economic cases", "Experience in civil cases: property, inheritance, family law", "Full support of corporate procedures"]}, publications: []
  },
  {
    id: 11,
    slug: "saidov-elyor",
    photo: "photos/saidov-elyor.jpeg",
    name: { ru: "Саидов Элёрбек", uz: "Saidov Elyorbek", en: "Elyorbek Saidov" },
    title: "Юрист",
    specialization: ["Корпоративное право", "Коммерческое право", "Инвестиционное право"],
    experience: "4+ лет",
    cases: "45+",
    initials: "СЭ",
    accentColor: "#2c3e6b",
    bio: { ru: "Юрист GSP LAW, специализирующийся на корпоративном, коммерческом и инвестиционном праве. Оказывает правовые услуги местным и иностранным клиентам по вопросам контрактного права, инвестиций, корпоративных структур и коммерческих споров.", uz: "GSP LAW yurist, korporativ, tijorat va investitsion huquq bo'yicha ixtisoslashgan. Shartnoma huquqi, investitsiyalar, korporativ tuzilmalar va tijorat nizolari bo'yicha mahalliy va xorijiy mijozlarga huquqiy xizmatlar ko'rsatadi.", en: "Lawyer at GSP LAW specializing in corporate, commercial and investment law. Provides legal services to local and foreign clients on contract law, investments, corporate structures and commercial disputes." },
    description: { ru: "Элёрбек Саидов имеет опыт в международных инвестиционных проектах, правовых аудитах, реструктуризации уставного капитала и нормативно-правовом соответствии. Разрабатывает коммерческие соглашения, ведёт переговоры и представляет клиентов в суде. Работает над развитием компетенций в области M&A и международной правовой практики.", uz: "Elyorbek Saidov xorijiy investitsiyalar, huquqiy auditlar, ustav kapitalini restrukturizatsiya qilish va normativ-huquqiy muvofiqlik loyihalarida tajribaga ega. Tijorat shartnomalari ishlab chiqadi, muzokaralar olib boradi va sudda mijozlar manfaatlarini himoya qiladi.", en: "Elyorbek Saidov has experience in international investment projects, legal audits, authorized capital restructuring and regulatory compliance. Drafts commercial agreements, conducts negotiations and represents clients in court. Developing expertise in M&A and international legal practice." },
    howIHelp: { ru: "Помогаю местным и иностранным компаниям в вопросах корпоративного структурирования, заключения контрактов, привлечения инвестиций и разрешения коммерческих споров в Узбекистане.", uz: "Mahalliy va xorijiy kompaniyalarga O'zbekistonda korporativ tuzilma, shartnomalar tuzish, investitsiyalar jalb qilish va tijorat nizolarini hal etish masalalarida yordam beraman.", en: "I help local and foreign companies with corporate structuring, contracting, attracting investments and resolving commercial disputes in Uzbekistan." },
    services: {ru: ["Корпоративное право", "Коммерческие контракты", "Инвестиционные проекты", "Правовой аудит", "Корпоративные споры", "M&A"], uz: ["Korporativ huquq", "Tijorat shartnomalari", "Investitsion loyihalar", "Huquqiy audit", "Korporativ nizolar", "M&A"], en: ["Corporate law", "Commercial contracts", "Investment projects", "Legal audit", "Corporate disputes", "M&A"]},
    blog: [], education: [
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" }
    ], achievements: {ru: ["Опыт в международных инвестиционных проектах", "Участие в реструктуризации уставного капитала компаний", "Разработка комплексных стратегий управления правовыми рисками"], uz: ["Xalqaro investitsion loyihalarda tajriba", "Kompaniyalar ustav kapitalini qayta tuzishda ishtirok etish", "Huquqiy risklarni boshqarishning kompleks strategiyalarini ishlab chiqish"], en: ["Experience in international investment projects", "Participation in restructuring of authorized capital of companies", "Development of comprehensive legal risk management strategies"]}, publications: []
  },
  {
    id: 12,
    slug: "zayniyev-mujohid",
    photo: "photos/zayniyev-mujohid.jpeg",
    name: { ru: "Зайниев Муджохид", uz: "Zayniev Mujohid", en: "Mujohid Zayniev" },
    title: "Адвокат",
    specialization: ["Бизнес-право", "Корпоративное право", "Уголовное право"],
    experience: "3+ лет",
    cases: "40+",
    initials: "ЗМ",
    accentColor: "#17435a",
    bio: { ru: "Адвокат GSP LAW с академическим фундаментом Ташкентского государственного юридического университета. Специализируется на защите бизнеса, корпоративном праве и уголовных делах. Выделяется стратегическим мышлением и применением инновационных цифровых решений в юридической практике.", uz: "Toshkent davlat yuridik universitetining akademik poydevori bilan GSP LAW advokati. Biznesni himoya qilish, korporativ huquq va jinoyat ishlariga ixtisoslashgan. Strategik fikrlashi va yuridik amaliyotda innovatsion raqamli yechimlarni qo'llashi bilan ajralib turadi.", en: "Advocate at GSP LAW with an academic foundation from Tashkent State University of Law. Specializes in business protection, corporate law and criminal cases. Stands out for strategic thinking and application of innovative digital solutions in legal practice." },
    description: { ru: "Муджохид Зайниев — молодой, но высококвалифицированный адвокат GSP LAW. Специализируется на бизнес-праве (создание компаний, инвестиции, корпоративная документация), корпоративном праве (споры акционеров, защита от рисков) и уголовном праве (особенно по экономическим, финансовым и бизнес-преступлениям). Применяет новейшие цифровые и системные решения в юридической практике.", uz: "Mujohid Zayniyev — GSP LAW ning yosh, lekin yuqori malakali advokati. Biznes huquqi (kompaniya ta'sisi, investitsiyalar, korporativ hujjatlar), korporativ huquq (aksiyadorlar nizolari, risklardan himoya) va jinoyat huquqi (ayniqsa iqtisodiy, moliyaviy va biznes jinoyatlari) bo'yicha ixtisoslashgan.", en: "Mujohid Zayniyev is a young but highly qualified advocate at GSP LAW. Specializes in business law (company incorporation, investments, corporate documentation), corporate law (shareholder disputes, risk protection) and criminal law (especially economic, financial and business crimes). Applies the latest digital and systemic solutions in legal practice." },
    howIHelp: { ru: "Помогаю бизнесу на всех стадиях — от создания компании до защиты от корпоративных рисков. Особая специализация — уголовная защита в делах, связанных с бизнесом и финансовыми преступлениями.", uz: "Biznesga barcha bosqichlarda yordam beraman — kompaniya ta'sisidan korporativ risklardan himoyagacha. Alohida ixtisoslashuv — biznes va moliyaviy jinoyatlar bilan bog'liq jinoyat ishlarida himoya.", en: "I help businesses at all stages — from company incorporation to protection against corporate risks. Special specialization — criminal defense in cases related to business and financial crimes." },
    services: {ru: ["Бизнес-право", "Корпоративное право", "Уголовная защита", "Создание компаний", "Инвестиции", "Акционерные споры"], uz: ["Biznes huquqi", "Korporativ huquq", "Jinoiy himoya", "Kompaniya ta'sisi", "Investitsiyalar", "Aksionerlik nizolari"], en: ["Business law", "Corporate law", "Criminal defense", "Company incorporation", "Investments", "Shareholder disputes"]},
    blog: [], education: [
      { degree: {ru: "Бакалавр права", uz: "Huquq bakalavri", en: "Bachelor of Laws"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "2025" }
    ], achievements: {ru: ["Специализация в уголовной защите по экономическим и финансовым делам", "Применение инновационных цифровых решений в юридической практике", "Комплексная правовая поддержка бизнеса на всех стадиях"], uz: ["Iqtisodiy va moliyaviy ishlarda jinoiy himoya bo'yicha ixtisoslashuv", "Yuridik amaliyotda innovatsion raqamli yechimlarni qo'llash", "Barcha bosqichlarda biznesni kompleks huquqiy qo'llab-quvvatlash"], en: ["Specialization in criminal defense in economic and financial cases", "Application of innovative digital solutions in legal practice", "Comprehensive legal support for business at all stages"]}, publications: []
  },
  {
    id: 13,
    slug: "sattorov-shohruh",
    photo: "photos/sattorov-shohruh.jpeg",
    name: { ru: "Саттаров Шохрух", uz: "Sattarov Shohruh", en: "Shohruh Sattarov" },
    title: "Юрист",
    specialization: ["Корпоративное право", "Коммерческое право", "Гражданское право"],
    experience: "4+ лет",
    cases: "50+",
    initials: "СШ",
    accentColor: "#1f3a5f",
    bio: { ru: "Юрист GSP LAW, специализирующийся на корпоративном и коммерческом праве. Оказывает правовую поддержку бизнесу в вопросах корпоративной документации, договорных отношений и гражданских споров.", uz: "GSP LAW yurist, korporativ va tijorat huquqiga ixtisoslashgan. Korporativ hujjatlar, shartnoma munosabatlari va fuqarolik nizolari masalalarida biznesga huquqiy yordam ko'rsatadi.", en: "Lawyer at GSP LAW specializing in corporate and commercial law. Provides legal support to businesses on corporate documentation, contractual relations and civil disputes." },
    description: { ru: "Шохрух Саттаров ведёт корпоративные и коммерческие дела, помогает клиентам в подготовке договоров и правовой документации, а также в разрешении гражданских споров на досудебном и судебном этапах.", uz: "Shohruh Sattorov korporativ va tijorat ishlarini olib boradi, shartnomalar va huquqiy hujjatlarni tayyorlashda mijozlarga yordam beradi, shuningdek fuqarolik nizolarini sudgacha va sud bosqichida hal qiladi.", en: "Shohruh Sattorov handles corporate and commercial cases, helps clients prepare contracts and legal documentation, and resolves civil disputes at pre-trial and trial stages." },
    howIHelp: { ru: "Помогаю компаниям и физическим лицам решать корпоративные и коммерческие вопросы, подготавливаю договоры и представляю клиентов в гражданских спорах.", uz: "Kompaniyalar va jismoniy shaxslarga korporativ va tijorat masalalarini hal etishga yordam beraman, shartnomalar tayyorlayman va fuqarolik nizolarida mijozlarni himoya qilaman.", en: "I help companies and individuals resolve corporate and commercial matters, prepare contracts and represent clients in civil disputes." },
    services: {ru: ["Корпоративная документация", "Коммерческие договоры", "Гражданские споры", "Правовая экспертиза"], uz: ["Korporativ hujjatlar", "Tijorat shartnomalari", "Fuqarolik nizolari", "Huquqiy ekspertiza"], en: ["Corporate documentation", "Commercial contracts", "Civil disputes", "Legal expertise"]},
    blog: [], education: [], achievements: {ru: [], uz: ["Korporativ va tijorat ishlarida strategik yondashuv", "Fuqarolik nizolarida sudgacha va sud bosqichlarida tajriba", "Shartnomalar va huquqiy hujjatlarni tayyorlash bo'yicha mutaxassis"], en: ["Strategic approach to corporate and commercial cases", "Experience in pre-trial and trial stages of civil disputes", "Specialist in preparing contracts and legal documentation"]}, publications: []
  },
  {
    id: 14,
    slug: "orinov-xayrullo",
    photo: "photos/orinov-xayrullo.jpeg",
    name: "O'rinov Xayrullo",
    title: "Адвокат",
    specialization: ["Корпоративное право", "Международное право", "Инвестиционный арбитраж"],
    experience: "3+ лет",
    cases: "30+",
    initials: "ОХ",
    accentColor: "#c9a96e",
    bio: { ru: "Адвокат GSP LAW, специализирующийся на корпоративном и международном праве. Консультирует бизнес-субъектов и защищает их интересы в государственных органах. Специализируется на международном коммерческом арбитраже и инвестиционных спорах.", uz: "GSP LAW advokati, korporativ va xalqaro huquq bo'yicha ixtisoslashgan. Biznes subyektlariga maslahat beradi va ularning manfaatlarini davlat organlarida himoya qiladi. Xalqaro tijorat arbitraji va investitsion nizolar bo'yicha ixtisoslashgan.", en: "Advocate at GSP LAW specializing in corporate and international law. Advises business entities and protects their interests in government authorities. Specializes in international commercial arbitration and investment disputes." },
    description: { ru: "Хайрулло О'ринов специализируется на правовой экспертизе коммерческих договоров, разработке контрактных структур и инвестиционном праве. Имеет опыт в работе с иностранными инвесторами при структурировании сделок и совместных предприятиях, применяя международную коммерческую практику (Incoterms, UNIDROIT, CISG). Нацелен на международный коммерческий арбитраж (ICC, SIAC, HKIAC) и инвестиционные споры ICSID.", uz: "Xayrullo O'rinov tijorat shartnomalari huquqiy ekspertizasi, shartnoma tuzilmalarini ishlab chiqish va investitsion huquq bo'yicha ixtisoslashgan. Xorijiy investorlar bilan bitimlar tuzish va qo'shma korxonalarda tajribaga ega, xalqaro tijorat amaliyotini (Incoterms, UNIDROIT, CISG) qo'llaydi.", en: "Xayrullo O'rinov specializes in legal review of commercial contracts, developing contract structures and investment law. Has experience working with foreign investors in deal structuring and joint ventures, applying international commercial practice (Incoterms, UNIDROIT, CISG). Focused on international commercial arbitration (ICC, SIAC, HKIAC) and ICSID investment disputes." },
    howIHelp: { ru: "Помогаю компаниям минимизировать регуляторные риски, структурировать договоры с иностранными партнёрами и защищать интересы в международных арбитражных разбирательствах.", uz: "Kompaniyalarga regulyator risklarni minimallashtirishda, xorijiy hamkorlar bilan shartnomalarni tuzilmalashtirishda va xalqaro arbitraj jarayonlarida manfaatlarni himoya qilishda yordam beraman.", en: "I help companies minimize regulatory risks, structure contracts with foreign partners and protect interests in international arbitration proceedings." },
    services: {ru: ["Корпоративное право", "Международный арбитраж", "Инвестиционные споры", "Коммерческие договоры", "Совместные предприятия", "Due Diligence"], uz: ["Korporativ huquq", "Xalqaro arbitraj", "Investitsion nizolar", "Tijorat shartnomalari", "Qo'shma korxonalar", "Due Diligence"], en: ["Corporate law", "International arbitration", "Investment disputes", "Commercial contracts", "Joint ventures", "Due Diligence"]},
    blog: [], education: [
      { degree: {ru: "Бакалавр права (LLB)", uz: "Huquq bakalavri (LLB)", en: "Bachelor of Laws (LLB)"}, institution: {ru: "Ташкентский государственный юридический университет", uz: "Toshkent davlat yuridik universiteti", en: "Tashkent State University of Law"}, year: "" }
    ], achievements: {ru: ["Специализация в международном коммерческом арбитраже (ICC, SIAC, HKIAC)", "Опыт в инвестиционных спорах в рамках ICSID", "Признание и исполнение иностранных арбитражных решений в Узбекистане"], uz: ["Xalqaro tijorat arbitrajida ixtisoslashuv (ICC, SIAC, HKIAC)", "ICSID doirasidagi investitsion nizolarda tajriba", "O'zbekistonda xorijiy arbitraj qarorlarini tan olish va ijro etish"], en: ["Specialization in international commercial arbitration (ICC, SIAC, HKIAC)", "Experience in ICSID investment disputes", "Recognition and enforcement of foreign arbitral awards in Uzbekistan"]}, publications: []
  },
  {
    id: 15,
    slug: "azimjon-zuxurov",
    photo: "photos/azimjon-zuxurov.jpeg",
    name: "Azimjon Zuxurov",
    title: "Адвокат | Профессиональный медиатор",
    specialization: ["Экономическое право", "Корпоративное право", "Медиация"],
    experience: "10+ лет",
    cases: "200+",
    initials: "AZ",
    accentColor: "#2d5a8e",
    bio: { ru: "Профессиональный адвокат с многолетним опытом в сложных экономических спорах, корпоративном управлении и правовой защите бизнеса. Медиа-эксперт с аудиторией 600 000+ в проекте «Yurist Zukhurov». Постоянный эксперт O'zbekiston24, Zo'r TV и Sevimli.", uz: "Murakkab iqtisodiy nizolar, korporativ boshqaruv va biznesni huquqiy himoya qilish sohasida ko'p yillik tajribaga ega professional advokat. \"Yurist Zukhurov\" loyihasi orqali 600 000+ auditoriyaga ega media-ekspert. O'zbekiston24, Zo'r TV va Sevimli kanallarining doimiy eksperti.", en: "Professional lawyer with years of experience in complex economic disputes, corporate governance and legal protection of business. Media expert with 600,000+ audience through the 'Yurist Zukhurov' project. Regular expert on O'zbekiston24, Zo'r TV and Sevimli channels." },
    description: { ru: "Азимжон Зухуров — профессиональный адвокат с уникальным сочетанием опыта государственного управления и судебной практики. Работал на ответственных должностях в государственном учреждении при Министерстве, что позволяет ему понимать систему изнутри. Сегодня — не только практикующий адвокат, но и признанный медиа-эксперт, системно содействующий верховенству закона в обществе через проект «Yurist Zukhurov» и регулярные выступления на ведущих телеканалах страны.", uz: "Azimjon Zuxurov — davlat boshqaruvi va sud amaliyotining noyob uyg'unligiga ega professional advokat. Vazirlik huzuridagi davlat muassasasida mas'uliyatli lavozimlarda faoliyat yuritgan, bu tizimni ichidan tushunishiga imkon beradi. Bugun u nafaqat amaliyotchi advokat, balki \"Yurist Zukhurov\" loyihasi va yetakchi telekanallar orqali jamiyatda qonun ustuvorligini ta'minlashga tizimli hissa qo'shayotgan media-ekspertdir.", en: "Azimjon Zuxurov is a professional lawyer with a unique combination of public administration and judicial practice experience. Worked in responsible positions at a government institution under the Ministry, giving him an inside understanding of the system. Today he is not only a practicing lawyer but also a recognized media expert systematically contributing to the rule of law through the 'Yurist Zukhurov' project and regular appearances on leading TV channels." },
    howIHelp: { ru: "Специализируюсь на защите бизнеса в сложных экономических и корпоративных спорах. Как профессиональный медиатор помогаю разрешать конфликты без суда. Мой опыт государственной службы позволяет эффективно взаимодействовать с государственными органами в интересах клиентов.", uz: "Murakkab iqtisodiy va korporativ nizolarda biznesni himoya qilishga ixtisoslanganman. Professional mediator sifatida nizolarni sudgacha hal etishga yordam beraman. Davlat xizmati tajribam davlat organlari bilan mijozlar manfaatlarida samarali ishlash imkonini beradi.", en: "I specialize in protecting business in complex economic and corporate disputes. As a professional mediator I help resolve conflicts without court. My public service experience allows effective interaction with government authorities in clients' interests." },
    services: {ru: ["Экономические споры", "Корпоративное управление", "Медиация", "Правовая защита бизнеса", "Взаимодействие с госорганами", "Консультации"], uz: ["Iqtisodiy nizolar", "Korporativ boshqaruv", "Mediatsiya", "Biznesni huquqiy himoyalash", "Davlat organlari bilan munosabatlar", "Konsultatsiyalar"], en: ["Economic disputes", "Corporate governance", "Mediation", "Legal protection of business", "Government relations", "Consulting"]},
    blog: [], education: [], achievements: {ru: ["Профессиональный медиатор", "Медиа-эксперт: проект «Yurist Zukhurov» — 600 000+ подписчиков", "Постоянный эксперт O'zbekiston24, Zo'r TV, Sevimli", "Опыт государственной службы при Министерстве"], uz: ["Professional mediator", "Media-ekspert: 'Yurist Zukhurov' loyihasi — 600 000+ obunachi", "O'zbekiston24, Zo'r TV, Sevimli kanallarining doimiy eksperti", "Vazirlik huzuridagi davlat xizmatida ish tajribasi"], en: ["Professional mediator", "Media expert: 'Yurist Zukhurov' project — 600,000+ subscribers", "Regular expert on O'zbekiston24, Zo'r TV, Sevimli channels", "Experience in public service under the Ministry"]}, publications: []
  },
]

/* ===== CASES ===== */
const CASES = [
  {
    id: 1, icon: '💻', color: '#1565c0', year: '2024', lawyer: 'Gulyamov S.S.',
    tag: { ru: 'IT-право', uz: 'IT huquqi', en: 'IT Law' },
    title: { ru: 'Победа в споре на $5.2 млн', uz: "$5.2 mlnlik nizoda g'alaba", en: 'Victory in a $5.2M Dispute' },
    desc: { ru: 'Успешная защита узбекского IT-стартапа в споре с международным партнёром по нарушению лицензионного соглашения. Урегулировано через медиацию без судебного разбирательства.', uz: "O'zbek IT-startapini xalqaro hamkor bilan litsenziya shartnomasi buzilishi bo'yicha nizoda muvaffaqiyatli himoya qilish. Sud jarayonisiz, mediatsiya orqali hal qilindi.", en: "Successful defense of an Uzbek IT startup in a dispute with an international partner over breach of a licensing agreement. Resolved through mediation without litigation." },
    result: { ru: 'Экономия $5.2 млн', uz: '$5.2 mln tejaldi', en: '$5.2M Saved' },
    challenge: { ru: 'Международный партнёр предъявил претензии на $5.2 млн, утверждая о нарушении эксклюзивного лицензионного соглашения. IT-стартап оказался под угрозой ликвидации.', uz: "Xalqaro hamkor eksklyuziv litsenziya shartnomasi buzilganini asos qilib, $5.2 mln miqdorida da'vo qo'ydi. IT-startap tugatilish xavfi ostida qoldi.", en: "An international partner filed a $5.2M claim, alleging breach of an exclusive licensing agreement. The IT startup faced the risk of liquidation." },
    approach: { ru: 'Провели детальный анализ договорной документации, выявили процедурные нарушения со стороны истца и подготовили контрпретензию. Инициировали медиацию в нейтральной юрисдикции.', uz: "Shartnoma hujjatlarini batafsil tahlil qildik, da'vogar tomonidan protsessual buzilishlarni aniqladik va qarshi da'vo tayyorladik. Neytral yurisdiksiyada mediatsiyani boshladik.", en: "We conducted a detailed analysis of the contractual documentation, identified procedural violations by the claimant, and prepared a counterclaim. We initiated mediation in a neutral jurisdiction." },
    duration: { ru: '4 месяца', uz: '4 oy', en: '4 months' },
    jurisdiction: { ru: 'Узбекистан / Международный арбитраж', uz: "O'zbekiston / Xalqaro arbitraj", en: 'Uzbekistan / International Arbitration' }
  },
  {
    id: 2, icon: '🛡️', color: '#37474f', year: '2024', lawyer: 'Mixliyev S.',
    tag: { ru: 'Уголовное право', uz: 'Jinoiy huquq', en: 'Criminal Law' },
    title: { ru: 'Прекращение уголовного дела против CEO', uz: "Bosh direktorga nisbatan qo'zg'atilgan jinoiy ish to'xtatildi", en: "Criminal Case Against CEO Dismissed" },
    desc: { ru: 'Защита генерального директора производственной компании от обвинений в уклонении от уплаты налогов. Дело прекращено на стадии следствия за отсутствием состава преступления.', uz: "Ishlab chiqarish kompaniyasi bosh direktorini soliqdan bo'yin tovlash aybida himoya qilish. Ish tergov bosqichida jinoyat tarkibi yo'qligi sababli to'xtatildi.", en: "Defense of a manufacturing company's CEO against tax evasion charges. The case was dismissed at the investigation stage due to the absence of a criminal offense." },
    result: { ru: 'Дело прекращено', uz: "Ish to'xtatildi", en: 'Case Dismissed' },
    challenge: { ru: 'Генеральный директор оказался под уголовным преследованием с угрозой лишения свободы до 5 лет. Компания рисковала прекратить деятельность.', uz: "Bosh direktor 5 yilgacha ozodlikdan mahrum etish xavfi bilan jinoiy javobgarlikka tortildi. Kompaniya faoliyatini to'xtatish xavfi ostida qoldi.", en: "The CEO faced criminal prosecution with a risk of up to 5 years in prison. The company risked having to cease operations." },
    approach: { ru: 'Обеспечили немедленный доступ к клиенту, провели параллельный налоговый аудит, доказали правомерность спорных операций документально. Оспорили процессуальные нарушения следствия.', uz: "Mijozga zudlik bilan huquqiy yordam ko'rsatildi, parallel soliq auditi o'tkazildi, bahsli operatsiyalarning qonuniyligi hujjatlar bilan isbotlandi. Tergovdagi protsessual buzilishlar shikoyat qilindi.", en: "We secured immediate access to the client, conducted a parallel tax audit, and documented the legality of the disputed transactions. We challenged procedural violations in the investigation." },
    duration: { ru: '3 месяца', uz: '3 oy', en: '3 months' },
    jurisdiction: { ru: 'Ташкент, Узбекистан', uz: "Toshkent, O'zbekiston", en: 'Tashkent, Uzbekistan' }
  },
  {
    id: 3, icon: '🤝', color: '#c9a96e', year: '2024', lawyer: "Sodiq A.",
    tag: { ru: 'M&A', uz: 'M&A', en: 'M&A' },
    title: { ru: 'Сопровождение сделки слияния на $18 млн — закрыта', uz: "$18 mlnlik birlashtirish bitimini qo'llab-quvvatlash — yakunlandi", en: "Advisory on an $18M Merger Deal — Closed" },
    desc: { ru: 'Юридическое сопровождение поглощения телеком-компании с активами в трёх регионах Узбекистана: due diligence, структурирование сделки, переговоры и закрытие.', uz: "O'zbekistonning uch hududidagi aktivlarga ega telekommunikatsiya kompaniyasini sotib olishni yuridik qo'llab-quvvatlash: due diligence, bitimni tuzish, muzokaralar va yakunlash.", en: "Legal support for the acquisition of a telecom company with assets in three regions of Uzbekistan: due diligence, deal structuring, negotiations, and closing." },
    result: { ru: 'Сделка закрыта', uz: 'Bitim yopildi', en: 'Deal Closed' },
    challenge: { ru: 'Сделка осложнялась скрытыми обязательствами цели, разногласиями акционеров и необходимостью регуляторного согласования в сфере телекоммуникаций.', uz: "Bitim maqsadli kompaniyaning yashirin majburiyatlari, aksiyadorlar o'rtasidagi kelishmovchiliklar va telekommunikatsiya sohasidagi regulyator roziligi zarurati bilan murakkablashdi.", en: "The deal was complicated by hidden liabilities of the target company, shareholder disagreements, and the need for regulatory approval in the telecommunications sector." },
    approach: { ru: 'Провели всестороннюю проверку (due diligence) за 6 недель, структурировали сделку с условиями escrow для снижения рисков. Добились согласования регулятора в рекордные сроки.', uz: "6 hafta ichida har tomonlama tekshiruv (due diligence) o'tkazdik, risklarni kamaytirish uchun eskrou shartlari bilan bitimni tuzdik. Regulyator roziligiga rekord muddatda erishdik.", en: "We conducted comprehensive due diligence within 6 weeks and structured the deal with escrow conditions to reduce risk. We secured regulatory approval in record time." },
    duration: { ru: '6 месяцев', uz: '6 oy', en: '6 months' },
    jurisdiction: { ru: 'Узбекистан', uz: "O'zbekiston", en: 'Uzbekistan' }
  },
  {
    id: 4, icon: '📊', color: '#c62828', year: '2023', lawyer: 'Isamutdinov U.',
    tag: { ru: 'Налоговое право', uz: 'Soliq huquqi', en: 'Tax Law' },
    title: { ru: 'Возврат незаконно взысканного НДС — $1.2 млн', uz: "Noqonuniy undirilgan QQS qaytarildi — $1.2 mln", en: "Recovery of Unlawfully Collected VAT — $1.2M" },
    desc: { ru: 'Успешное оспаривание решения налоговых органов и возврат незаконно взысканных сумм НДС и налога на прибыль для крупного производственного предприятия.', uz: "Yirik ishlab chiqarish korxonasi uchun soliq organlari qarorini muvaffaqiyatli shikoyat qilish va noqonuniy undirilgan QQS hamda foyda solig'i summalarini qaytarish.", en: "Successful challenge of a tax authority decision and recovery of unlawfully collected VAT and income tax for a large manufacturing enterprise." },
    result: { ru: 'Возвращено $1.2 млн', uz: '$1.2 mln qaytarildi', en: '$1.2M Recovered' },
    challenge: { ru: 'Налоговые органы доначислили $1.2 млн НДС и налога на прибыль, ссылаясь на ненадлежащее оформление экспортных операций. Угроза банкротства предприятия.', uz: "Soliq organlari eksport operatsiyalarining noto'g'ri rasmiylashtirilganiga asoslanib, $1.2 mln QQS va foyda solig'i qo'shimcha hisobladi. Korxona bankrotlik xavfi ostida qoldi.", en: "Tax authorities assessed an additional $1.2M in VAT and income tax, citing improper documentation of export operations. The enterprise faced the threat of bankruptcy." },
    approach: { ru: 'Провели анализ 3 лет первичной документации, доказали правомерность налоговых вычетов. Представляли интересы клиента во всех инстанциях — от налоговой до Высшего суда.', uz: "3 yillik birlamchi hujjatlarni tahlil qildik, soliq chegirmalarining qonuniyligini isbotladik. Mijoz manfaatlarini barcha instansiyalarda — soliq idorasidan tortib Oliy sudgacha — himoya qildik.", en: "We analyzed 3 years of primary documentation and proved the legitimacy of the tax deductions. We represented the client's interests at all levels — from the tax authority to the Supreme Court." },
    duration: { ru: '8 месяцев', uz: '8 oy', en: '8 months' },
    jurisdiction: { ru: 'Узбекистан, судебные инстанции всех уровней', uz: "O'zbekiston, barcha darajadagi sud instansiyalari", en: 'Uzbekistan, courts at all levels' }
  },
  {
    id: 5, icon: '💡', color: '#6a1b9a', year: '2024', lawyer: 'Alijonova D.',
    tag: { ru: 'Интеллект. собственность', uz: 'Intellektual mulk', en: 'Intellectual Property' },
    title: { ru: 'Защита бренда от международного плагиата', uz: 'Brendni xalqaro plagiatdan himoya qilish', en: 'Brand Protection Against International Plagiarism' },
    desc: { ru: 'Регистрация товарного знака и защита исключительных прав клиента против иностранного конкурента, незаконно использовавшего идентичный бренд на рынке Узбекистана.', uz: "Tovar belgisini ro'yxatdan o'tkazish va O'zbekiston bozorida bir xil brenddan noqonuniy foydalangan xorijiy raqobatchiga qarshi mijozning eksklyuziv huquqlarini himoya qilish.", en: "Trademark registration and protection of the client's exclusive rights against a foreign competitor who unlawfully used an identical brand in the Uzbek market." },
    result: { ru: 'Бренд защищён', uz: 'Brend himoya qilindi', en: 'Brand Protected' },
    challenge: { ru: 'Иностранная компания использовала идентичный бренд клиента на территории Узбекистана, создавая путаницу на рынке и нанося ущерб репутации.', uz: "Xorijiy kompaniya O'zbekiston hududida mijozning brendiga bir xil brenddan foydalanib, bozorda chalkashlik keltirib chiqardi va obro'ga putur yetkazdi.", en: "A foreign company used an identical brand to the client's on the territory of Uzbekistan, creating market confusion and causing reputational damage." },
    approach: { ru: 'Провели параллельную регистрацию товарного знака по системе Мадрида, подали иск о пресечении незаконного использования и взыскании убытков.', uz: "Madrid tizimi bo'yicha tovar belgisini parallel ro'yxatdan o'tkazdik, noqonuniy foydalanishni to'xtatish va zararlarni undirish bo'yicha da'vo qo'zg'atdik.", en: "We conducted parallel trademark registration under the Madrid System and filed a lawsuit to stop the unlawful use and recover damages." },
    duration: { ru: '5 месяцев', uz: '5 oy', en: '5 months' },
    jurisdiction: { ru: 'Узбекистан / Международная система Мадрида', uz: "O'zbekiston / Xalqaro Madrid tizimi", en: 'Uzbekistan / International Madrid System' }
  },
  {
    id: 6, icon: '👥', color: '#00695c', year: '2024', lawyer: 'Ergasheva S.',
    tag: { ru: 'Трудовое право', uz: 'Mehnat huquqi', en: 'Labor Law' },
    title: { ru: 'Коллективный трудовой спор с 47 сотрудниками', uz: '47 xodim bilan jamoaviy mehnat nizosi', en: 'Collective Labor Dispute with 47 Employees' },
    desc: { ru: 'Представление интересов крупной компании в коллективном трудовом споре. Достигнуто мировое соглашение на условиях, полностью защищающих интересы работодателя.', uz: "Yirik kompaniya manfaatlarini jamoaviy mehnat nizosida himoya qilish. Ish beruvchi manfaatlarini to'liq himoya qiluvchi shartlarda sulh kelishuviga erishildi.", en: "Representation of a major company in a collective labor dispute. A settlement agreement was reached on terms fully protecting the employer's interests." },
    result: { ru: 'Мировое соглашение', uz: 'Sulh kelishuvi', en: 'Settlement Reached' },
    challenge: { ru: 'Организованная группа из 47 сотрудников подала коллективный иск с требованиями на сумму свыше $800 тысяч. Риск репутационного ущерба и медиаогласки.', uz: "47 xodimdan iborat uyushgan guruh $800 mingdan ortiq miqdordagi talablar bilan jamoaviy da'vo qo'zg'atdi. Obro'ga putur yetkazish va ommaviy axborot vositalarida yoritilish xavfi mavjud edi.", en: "An organized group of 47 employees filed a collective lawsuit with claims exceeding $800,000. There was a risk of reputational damage and media exposure." },
    approach: { ru: 'Провели аудит трудовой документации, выявили процессуальные слабости исков. Организовали конфиденциальные переговоры и достигли мирового соглашения на выгодных условиях.', uz: "Mehnat hujjatlarini audit qildik, da'volardagi protsessual kamchiliklarni aniqladik. Maxfiy muzokaralarni tashkil qildik va foydali shartlarda sulh kelishuviga erishdik.", en: "We audited the labor documentation and identified procedural weaknesses in the claims. We organized confidential negotiations and reached a settlement on favorable terms." },
    duration: { ru: '2.5 месяца', uz: '2,5 oy', en: '2.5 months' },
    jurisdiction: { ru: 'Ташкент, Узбекистан', uz: "Toshkent, O'zbekiston", en: 'Tashkent, Uzbekistan' }
  }
];

/* ===== METRICS ===== */
const METRICS = [
  { num: "94%",   key: "winRate",      icon: "🏆" },
  { num: "$250M+",key: "portfolioVal", icon: "💼" },
  { num: "45+",   key: "intlCases",    icon: "🌐" },
  { num: "98%",   key: "satisfaction", icon: "⭐" },
  { num: "15+",   key: "industries",   icon: "🏢" },
  { num: "1000+", key: "clients",      icon: "🤝" },
  { num: "16+",   key: "yearsOnMkt",   icon: "📅" },
  { num: "3",     key: "languages",    icon: "🗣️" },
  { num: "24/7",  key: "support",      icon: "🔔" }
];

/* ===== NEWS ===== */
const NEWS = [
  {
    id: 1, tagColor: '#4527a0',
    tag: { ru: 'AI-право', uz: 'AI-huquq', en: 'AI Law' },
    date: { ru: 'Апрель 2026', uz: '2026-yil aprel', en: 'April 2026' },
    title: { ru: 'Закон об ИИ ЕС 2026: полное применение с августа. Что нужно знать бизнесу', uz: "EI 2026-yilgi sun'iy intellekt qonuni: avgustdan to'liq amal qiladi. Biznes uchun nima muhim", en: 'EU AI Act 2026: Full Application from August. What Businesses Need to Know' },
    excerpt: { ru: 'С 2 августа 2026 года EU AI Act вступает в полную силу. Каждая страна-член ЕС обязана создать национальный регуляторный «песочницы» для ИИ. Эксперты предупреждают: аналогичное регулирование в СНГ неизбежно.', uz: "2026-yil 2-avgustdan EI sun'iy intellekt to'g'risidagi qonuni to'liq kuchga kiradi. Har bir EI a'zo davlati sun'iy intellekt uchun milliy tartibga soluvchi \"qumloq\" yaratishi shart. Ekspertlar: MDH davlatlarida ham shunga o'xshash tartibga solish muqarrar, deb ogohlantirmoqda.", en: 'Starting August 2, 2026, the EU AI Act comes into full force. Every EU member state must establish a national regulatory "sandbox" for AI. Experts warn that similar regulation in the CIS is inevitable.' },
    source: 'European Commission',
    url: 'https://artificialintelligenceact.eu/'
  },
  {
    id: 2, tagColor: '#1565c0',
    tag: { ru: 'Конфиденциальность', uz: 'Maxfiylik', en: 'Privacy' },
    date: { ru: 'Январь 2026', uz: '2026-yil yanvar', en: 'January 2026' },
    title: { ru: 'Privacy & Cybersecurity 2025–2026: вызовы и тренды для бизнеса', uz: 'Maxfiylik va kiberxavfsizlik 2025–2026: biznes uchun sinovlar va tendensiyalar', en: 'Privacy & Cybersecurity 2025–2026: Challenges and Trends for Business' },
    excerpt: { ru: 'White & Case опубликовал обзор ключевых изменений в законодательстве о защите данных. Число штатов США с действующими законами о конфиденциальности выросло с 9 до 20. Глобальный тренд — ужесточение киберответственности.', uz: "White & Case ma'lumotlarni himoya qilish qonunchiligidagi asosiy o'zgarishlar sharhini e'lon qildi. Maxfiylik to'g'risidagi qonunlari amal qiluvchi AQSh shtatlari soni 9 tadan 20 taga oshdi. Global tendensiya — kiber javobgarlikning kuchayishi.", en: 'White & Case published an overview of key changes in data protection legislation. The number of US states with active privacy laws grew from 9 to 20. The global trend is toward stricter cyber liability.' },
    source: 'White & Case LLP',
    url: 'https://www.whitecase.com/insight-alert/privacy-and-cybersecurity-2025-2026-insights-challenges-and-trends-ahead'
  },
  {
    id: 3, tagColor: '#e65100',
    tag: { ru: 'Крипто / Финтех', uz: 'Kripto / Fintex', en: 'Crypto / Fintech' },
    date: { ru: 'Январь 2026', uz: '2026-yil yanvar', en: 'January 2026' },
    title: { ru: 'Цифровые активы 2025–2026: знаковый год и новые горизонты', uz: "Raqamli aktivlar 2025–2026: muhim yil va yangi ufqlar", en: 'Digital Assets 2025–2026: A Landmark Year and New Horizons' },
    excerpt: { ru: 'Cleary Gottlieb подвёл итоги переломного 2025 года для регулирования крипторынка: принятие GENIUS Act в США, полное внедрение MiCA в ЕС, реформы KYC/AML. Рынок вступает в фазу зрелого регулирования.', uz: "Cleary Gottlieb kriptobozorni tartibga solishda burilish nuqtasi bo'lgan 2025-yil natijalarini yakunladi: AQShda GENIUS Act qabul qilinishi, EIda MiCA to'liq joriy etilishi, KYC/AML islohotlari. Bozor barqaror tartibga solish bosqichiga kirmoqda.", en: 'Cleary Gottlieb summarized the pivotal year of 2025 for crypto market regulation: the adoption of the GENIUS Act in the US, full implementation of MiCA in the EU, and KYC/AML reforms. The market is entering a phase of mature regulation.' },
    source: 'Cleary Gottlieb',
    url: 'https://www.clearygottlieb.com/news-and-insights/publication-listing/2026-digital-assets-regulatory-update-a-landmark-2025-but-more-developments-on-the-horizon'
  },
  {
    id: 4, tagColor: '#00695c',
    tag: { ru: 'Арбитраж', uz: 'Arbitraj', en: 'Arbitration' },
    date: { ru: 'Январь 2026', uz: '2026-yil yanvar', en: 'January 2026' },
    title: { ru: 'Тренды международного арбитража 2026: ИИ, торговые споры и новые правила', uz: "2026-yilgi xalqaro arbitraj tendensiyalari: sun'iy intellekt, savdo nizolari va yangi qoidalar", en: 'International Arbitration Trends 2026: AI, Trade Disputes, and New Rules' },
    excerpt: { ru: 'Cleary Gottlieb выявил ключевые тенденции: рост споров M&A и ценных бумаг, интеграция ИИ в арбитражные процессы, новые арбитражные законы Англии (2025) и Китая (2026), усиление ОАЭ как площадки для разрешения споров.', uz: "Cleary Gottlieb asosiy tendensiyalarni aniqladi: M&A va qimmatli qog'ozlar bo'yicha nizolarning o'sishi, sun'iy intellektning arbitraj jarayonlariga integratsiyasi, Angliya (2025) va Xitoy (2026)ning yangi arbitraj qonunlari, BAA ning nizolarni hal qilish maydonchasi sifatida mustahkamlanishi.", en: "Cleary Gottlieb identified key trends: rising M&A and securities disputes, AI integration into arbitration processes, new arbitration laws in England (2025) and China (2026), and the UAE's strengthening role as a dispute resolution hub." },
    source: 'Cleary Gottlieb',
    url: 'https://www.clearygottlieb.com/news-and-insights/publication-listing/international-arbitration-trends-and-topics-for-2026'
  },
  {
    id: 5, tagColor: '#2e7d32',
    tag: { ru: 'M&A', uz: 'M&A', en: 'M&A' },
    date: { ru: 'Декабрь 2025', uz: '2025-yil dekabr', en: 'December 2025' },
    title: { ru: 'M&A 2025: рекордный год и прогноз на 2026. ИИ-сделки доминируют', uz: "M&A 2025: rekord yil va 2026-yilga prognoz. Sun'iy intellekt bitimlari ustunlik qiladi", en: 'M&A 2025: A Record Year and 2026 Outlook. AI Deals Dominate' },
    excerpt: { ru: 'По итогам 2025 года рынок слияний и поглощений установил рекорды. SoftBank вложил $40 млрд в OpenAI. Проект Stargate — $500 млрд в AI-инфраструктуру. В 2026 году ожидается дальнейший рост транзакций в секторе ИИ.', uz: "2025-yil yakunlariga ko'ra birlashish va qo'shib olish bozori rekordlar o'rnatdi. SoftBank OpenAI ga $40 mlrd sarmoya kiritdi. Stargate loyihasi — sun'iy intellekt infratuzilmasiga $500 mlrd. 2026-yilda sun'iy intellekt sektorida bitimlarning yanada o'sishi kutilmoqda.", en: "The 2025 M&A market set records. SoftBank invested $40B in OpenAI. The Stargate project committed $500B to AI infrastructure. Further growth in AI-sector transactions is expected in 2026." },
    source: 'Cleary Gottlieb',
    url: 'https://www.clearygottlieb.com/news-and-insights/publication-listing/ma-2025-in-review-and-a-look-ahead-to-2026'
  },
  {
    id: 6, tagColor: '#c62828',
    tag: { ru: 'Данные / Технологии', uz: "Ma'lumotlar / Texnologiyalar", en: 'Data / Technology' },
    date: { ru: 'Январь 2026', uz: '2026-yil yanvar', en: 'January 2026' },
    title: { ru: 'Baker McKenzie: что ждёт сферу данных, технологий и кибербезопасности в 2026', uz: "Baker McKenzie: 2026-yilda ma'lumotlar, texnologiyalar va kiberxavfsizlik sohasini nima kutmoqda", en: "Baker McKenzie: What's on the Horizon for Data, Technology, and Cybersecurity in 2026" },
    excerpt: { ru: 'Ведущая международная фирма опубликовала прогноз: ужесточение технических и организационных требований по кибербезопасности, обязательные оценки рисков, управление цепочками поставок и новые органы по киберрегулированию.', uz: "Yetakchi xalqaro firma prognozni e'lon qildi: kiberxavfsizlik bo'yicha texnik va tashkiliy talablarning kuchayishi, majburiy risk baholari, ta'minot zanjirlarini boshqarish va yangi kiber-tartibga solish organlari.", en: 'A leading international firm published its forecast: stricter technical and organizational cybersecurity requirements, mandatory risk assessments, supply chain management, and new cyber-regulatory bodies.' },
    source: 'Baker McKenzie',
    url: 'https://www.bakermckenzie.com/en/insight/publications/2026/01/whats-on-the-horizon-for-data-technology'
  },
  {
    id: 7, tagColor: '#37474f',
    tag: { ru: 'AI-законы США', uz: "AQSh sun'iy intellekt qonunlari", en: 'US AI Laws' },
    date: { ru: 'Апрель 2026', uz: '2026-yil aprel', en: 'April 2026' },
    title: { ru: 'Битва за регулирование ИИ: федеральный уровень против законов штатов', uz: "Sun'iy intellektni tartibga solish uchun kurash: federal daraja shtat qonunlariga qarshi", en: 'The Battle Over AI Regulation: Federal Level vs. State Laws' },
    excerpt: { ru: 'В 2025 году в США было внесено более 1 000 законопроектов об ИИ. Белый дом создал «AI Litigation Task Force» для оспаривания законов штатов. Colorado AI Act вступит в силу 30 июня 2026 года.', uz: "2025-yilda AQShda sun'iy intellekt bo'yicha 1000 dan ortiq qonun loyihasi kiritildi. Oq uy shtat qonunlariga qarshi chiqish uchun \"AI Litigation Task Force\" tuzdi. Colorado AI Act 2026-yil 30-iyundan kuchga kiradi.", en: "In 2025, more than 1,000 AI-related bills were introduced in the US. The White House created an 'AI Litigation Task Force' to challenge state laws. The Colorado AI Act takes effect on June 30, 2026." },
    source: 'Cooley LLP',
    url: 'https://www.cooley.com/news/insight/2026/2026-04-24-state-ai-laws-where-are-they-now'
  },
  {
    id: 8, tagColor: '#558b2f',
    tag: { ru: 'Крипто — глобально', uz: 'Kripto — global', en: 'Crypto — Global' },
    date: { ru: 'Март 2026', uz: '2026-yil mart', en: 'March 2026' },
    title: { ru: 'Крипторегулирование 2026: демократизация цифровых активов', uz: 'Kriptoregulyatsiya 2026: raqamli aktivlarni demokratlashtirish', en: 'Crypto Regulation 2026: The Democratization of Digital Assets' },
    excerpt: { ru: 'K&L Gates: 2026 год станет поворотным для институционального принятия цифровых активов. Банковские регуляторы расширяют перечень разрешённых операций с криптовалютой. GENIUS Act начинает реализацию.', uz: "K&L Gates: 2026-yil raqamli aktivlarni institutsional qabul qilish uchun burilish nuqtasi bo'ladi. Bank regulyatorlari kriptovalyuta bilan ruxsat etilgan operatsiyalar ro'yxatini kengaytirmoqda. GENIUS Act amalga oshirila boshlaydi.", en: "K&L Gates: 2026 will be a turning point for institutional adoption of digital assets. Banking regulators are expanding the list of permitted cryptocurrency operations. The GENIUS Act begins implementation." },
    source: 'K&L Gates',
    url: 'https://www.klgates.com/Crypto-in-2026-The-Democratization-of-Digital-Assets-1-29-2026'
  }
];

/* ===== I18N / TRANSLATIONS ===== */
const LANG = {
  ru: {
    nav: { about: 'О нас', services: 'Услуги', team: 'Команда', cases: 'Кейсы', consult: 'Консультация', news: 'Новости' },
    stats: ['лет опыта', 'портфель кейсов', 'адвокатов', 'клиентов'],
    hero: {
      tag: 'Юридическая фирма в Ташкенте',
      desc: 'Узкопрофильная команда экспертов в сфере IT-права, корпоративного права и разрешения экономических споров',
      btn1: 'Наша команда', btn2: 'Получить консультацию'
    },
    about: {
      sTag: 'О фирме', sTitle: 'Профессионализм. Доверие. Результат.',
      p1: 'GSP LAW FIRM — узкопрофильная юридическая фирма, специализирующаяся на комплексном правовом сопровождении IT-бизнеса, стартапов и коммерческих организаций в Узбекистане и за рубежом.',
      p2: 'Наша команда объединяет опытных адвокатов с глубокими знаниями в области киберправа, корпоративного права, налогового и банковского законодательства.',
      li: ['Высокий профессионализм','Индивидуальный подход к каждому клиенту','Оперативность и чёткость в работе','Абсолютная конфиденциальность'],
      mTitle: 'Наша миссия', mText: 'Мы ставим интересы клиента на первое место, обеспечивая максимальную защиту прав и законных интересов в любой правовой ситуации.',
      yearsLabel: 'лет',
      teamTag: 'Ключевые партнёры', teamTitle: 'Основатели и партнёры'
    },
    metrics: {
      sTag: 'Показатели', sTitle: 'Эффективность в цифрах', sDesc: 'Результаты, которые говорят сами за себя',
      winRate: 'Победный процент', portfolioVal: 'Стоимость портфеля', combinedExp: 'Лет совокупного опыта',
      intlCases: 'Международных дел', satisfaction: 'Удовлетворённость клиентов', industries: 'Отраслей практики',
      clients: 'Клиентов обслужено', yearsOnMkt: 'Лет на рынке', languages: 'Языка практики', support: 'Поддержка клиентов'
    },
    services: {
      sTag: 'Практика', sTitle: 'Области права', sDesc: 'Комплексное юридическое сопровождение бизнеса по всем ключевым направлениям',
      items: [
        { title: 'Корпоративное право и M&A', desc: 'Сопровождение сделок слияния и поглощения, корпоративное структурирование, акционерные соглашения' },
        { title: 'IT и киберправо', desc: 'Правовое сопровождение IT-компаний, стартапов, защита персональных данных и кибербезопасность' },
        { title: 'Банковское и финансовое право', desc: 'Регуляторные вопросы, финтех, лицензирование, финансовые транзакции' },
        { title: 'Налоговая практика', desc: 'Налоговое планирование, оптимизация, споры с налоговыми органами' },
        { title: 'Экономические споры', desc: 'Представление интересов в арбитражных судах, медиация, переговоры' },
        { title: 'Таможенное право', desc: 'Сопровождение ВЭД, таможенное оформление, споры с таможенными органами' },
        { title: 'Уголовная защита бизнеса', desc: 'Защита предпринимателей и руководителей в рамках уголовных дел' },
        { title: 'Трудовое право', desc: 'Трудовые договоры, споры с работниками, кадровое делопроизводство' },
        { title: 'Интеллектуальная собственность', desc: 'Регистрация товарных знаков, патентование, защита авторских прав' },
        { title: 'Постоянное обслуживание', desc: 'Комплексное юридическое сопровождение коммерческих организаций на постоянной основе' },
        { title: 'Контрактное право', desc: 'Разработка и экспертиза договоров, переговоры, урегулирование разногласий' },
        { title: 'Недвижимость', desc: 'Сопровождение сделок с недвижимостью, девелоперские проекты, арендные споры' }
      ]
    },
    cases: {
      sTag: 'Кейсы', sTitle: 'Выигранные дела', sDesc: 'Реальные результаты, которых мы добились для наших клиентов', result: 'Результат', year: 'Год', lawyer: 'Адвокат',
      allCasesBtn: 'Все кейсы →'
    },
    lawyers: {
      sTag: 'Команда', sTitle: 'Наши адвокаты и юристы', sDesc: 'Каждый специалист имеет глубокую экспертизу в своей области права', exp: 'опыт', casesLbl: 'дел', more: 'Подробнее →',
      titleMap: {},
      specMap: {}
    },
    news: { sTag: 'Новости', sTitle: 'Право и технологии', sDesc: 'Актуальные новости о кибербезопасности, IT-праве и юридическом мире — 2025', read: 'Читать далее →' },
    contact: {
      sTag: 'Контакты', sTitle: 'Свяжитесь с нами', sDesc: 'Первая консультация — бесплатно. Мы ответим в течение часа.',
      addr: 'Адрес', phone: 'Телефон', email: 'Email', formTitle: 'Задать вопрос',
      ph: { name: 'Ваше имя', tel: 'Номер телефона', email: 'Email (необязательно)', svc: 'Выберите услугу', msg: 'Кратко опишите вашу ситуацию или вопрос...' },
      submit: 'Отправить запрос →', success: '✓ Запрос отправлен! Мы свяжемся с вами в ближайшее время.', error: 'Не удалось отправить запрос. Попробуйте позже или позвоните нам.',
      svcOptions: ['Корпоративное право и M&A','IT и киберправо','Налоговая практика','Банковское и финансовое право','Трудовое право','Интеллектуальная собственность','Таможенное право','Уголовная защита бизнеса','Экономические споры','Другое']
    },
    footer: {
      rights: '© 2026 GSP LAW — Gulyamov, Sadikov and Partners. Все права защищены.',
      sTitle: 'Услуги', cTitle: 'Контакты',
      servicesList: ['Корпоративное право','IT и киберправо','Налоговая практика','Банковское право','Трудовое право','Интеллект. собственность']
    },
    lp: {
      back: 'Назад к команде', bio: 'Биография', help: 'Как я могу помочь', services: 'Услуги',
      consultTitle: 'Записаться на консультацию', sendBtn: 'Отправить запрос',
      expLbl: 'Опыт работы', casesLbl: 'Завершённых дел', firm: 'Фирма', office: 'Офис',
      blogTag: 'Блог', blogDesc: 'Экспертные статьи и аналитика', info: 'Информация',
      educationTitle: 'Образование', achievementsTitle: 'Достижения и награды', publicationsTitle: 'Публикации', certificatesTitle: 'Сертификаты и удостоверения',
      otherTag: 'Команда', otherTitle: 'Другие специалисты', allTeam: 'Вся команда →', readMore: 'Читать далее →',
      heroTag: 'Специалист GSP LAW FIRM', visitWebsite: '🔗 Вебсайт', notFound: 'Страница не найдена'
    },
    casesPage: {
      heroTag: 'Наша практика', heroTitle: 'Выигранные дела', heroDesc: 'Реальные результаты для реальных клиентов',
      challenge: 'Задача', approach: 'Наш подход', outcome: 'Результат',
      durationLabel: 'Длительность', jurLabel: 'Юрисдикция', lawyerLabel: 'Адвокат',
      filterAll: 'Все дела',
      backBtn: '← На главную'
    }
  },
  uz: {
    nav: { about: 'Biz haqimizda', services: 'Xizmatlar', team: 'Jamoa', cases: 'Ishlar', consult: 'Konsultatsiya', news: 'Yangiliklar' },
    stats: ['yillik tajriba', 'ish portfeli', 'advokat', 'mijozlar'],
    hero: {
      tag: 'Toshkentdagi yuridik firma',
      desc: "IT-huquq, korporativ huquq va iqtisodiy nizolarni hal etish sohasidagi mutaxassislar jamoasi",
      btn1: 'Bizning jamoa', btn2: 'Konsultatsiya olish'
    },
    about: {
      sTag: 'GSP LAW FIRM haqida', sTitle: 'Professionallik. Ishonch. Natija.',
      p1: "GSP LAW FIRM — IT-biznes, startaplar va tijorat tashkilotlarini O'zbekiston va xorijda yuridik jihatdan to'liq qo'llab-quvvatlashga ixtisoslashgan yuridik firma.",
      p2: 'Bizning jamoamiz kiberhuquq, korporativ huquq, soliq va bank qonunchiligida chuqur bilimlarga ega tajribali advokatlarni birlashtiradi.',
      li: ["Yuqori professionallik","Har bir mijozga individual yondashuv","Tezkorlik va aniqlik","To'liq maxfiylik"],
      mTitle: 'Bizning missiyamiz', mText: "Biz mijoz manfaatlarini birinchi o'ringa qo'yamiz, har qanday huquqiy vaziyatda huquq va qonuniy manfaatlarni maksimal darajada himoya qilamiz.",
      yearsLabel: 'yil',
      teamTag: 'Asosiy hamkorlar', teamTitle: 'Asoschilar va sheriklar'
    },
    metrics: {
      sTag: 'Ko\'rsatkichlar', sTitle: 'Raqamlarda samaradorlik', sDesc: "O'z-o'zidan gapiradigan natijalar",
      winRate: "G'alaba foizi", portfolioVal: 'Mijozlar manfaatida yutilgan summa', combinedExp: 'Umumiy tajriba yillari',
      intlCases: 'Xalqaro ishlar', satisfaction: 'Mijozlar mamnuniyati', industries: 'Amaliyot sohalari',
      clients: 'Xizmat ko\'rsatilgan mijozlar', yearsOnMkt: 'Bozorda yillar', languages: 'Amaliyot tillari', support: 'Mijozlarni qo\'llab-quvvatlash'
    },
    services: {
      sTag: 'Amaliyot', sTitle: "Yo'nalishlar", sDesc: "Biznesingizni har tomonlama himoya qilamiz — qonuniy, ishonchli, tez",
      items: [
        { title: 'Kompaniya tuzish va birlashtirish', desc: "Yangi biznes ochasizmi yoki boshqa kompaniya bilan qo'shilasizmi — hujjatlardan tortib imzogacha hamma narsani biz hal qilamiz" },
        { title: 'IT va raqamli biznes', desc: "Dastur, ilova, sayt yoki startap — texnologiya biznesingizni qonun doirasida to'g'ri yo'lga qo'yib beramiz" },
        { title: 'Islom banki va islom moliyasi', desc: "Islom moliyasi tamoyillari asosida kredit, litsenziya va moliyaviy operatsiyalar — nazorat organlari bilan ishlashda yoningizda bo'lamiz" },
        { title: 'Soliqlar', desc: "Soliq tekshiruvi keldi yoki ko'p to'layapsizmi? Qonun doirasida soliq yukini kamaytirib, muammolarni hal qilamiz" },
        { title: 'Biznes nizolari', desc: "Hamkor, mijoz yoki davlat organi bilan muammo chiqdi — sudda va muzokarada sizning manfaatingizni himoya qilamiz" },
        { title: 'Import va eksport', desc: "Chet elga tovar chiqarasizmi yoki olib kirasizmi? Bojxona hujjatlarini to'g'ri rasmiylashtirib, to'siqlarni bartaraf etamiz" },
        { title: 'Jinoiy ta\'qibdan himoya', desc: "Tadbirkor yoki rahbarga nisbatan jinoiy ish qo'zg'atildi — tergovdan sudgacha sizni himoya qilamiz" },
        { title: 'Xodimlar va mehnat masalalari', desc: "Ishchi bilan mojaromi, noto'g'ri ishdan bo'shatishmi yoki mehnat shartnomasi kerakmi — barchasi bizda" },
        { title: 'Brend va kashfiyot himoyasi', desc: "Brendingiz, logotipingiz yoki ixtiroyingizni ro'yxatdan o'tkazib, boshqalar nusxa ko'chirmasligi uchun himoyalaymiz" },
        { title: "Doimiy yuridik xizmat", desc: "Har oy yoningizda tayyor advokat — savollar, hujjatlar, shartnomalar — hammasini o'z vaqtida hal qilamiz" },
        { title: 'Shartnomalar', desc: "Imzolashdan oldin shartnomangizni tekshirib beramiz yoki siz uchun yangi, xavfsiz shartnoma tayyorlaymiz" },
        { title: "Uy-joy va ko'chmas mulk", desc: "Uy, ofis yoki yer sotib olasizmi? Hujjatlarni tekshirib, xavfsiz bitim tuzishingizga yordam beramiz" }
      ]
    },
    cases: {
      sTag: 'Ishlar', sTitle: "G'alaba qozonilgan ishlar", sDesc: 'Mijozlarimiz uchun erishilgan real natijalar', result: 'Natija', year: 'Yil', lawyer: 'Advokat',
      allCasesBtn: "Barcha ishlar →"
    },
    lawyers: {
      sTag: 'Jamoa', sTitle: 'Bizning advokatlar va yuristlar', sDesc: "Har bir mutaxassis o'z huquq sohasida chuqur tajribaga ega", exp: 'tajriba', casesLbl: 'ish', more: 'Batafsil →',
      titleMap: {
        'Партнёр, Профессор': 'Sherik, Professor',
        'Управляющий партнёр': 'Boshqaruvchi sherik',
        'Партнёр, Корпоративный юрист': 'Sherik, Korporativ yurist',
        'Партнёр, Специалист по контрактам': 'Sherik, Shartnoma mutaxassisi',
        'Партнёр | Руководитель отдела корпоративного обслуживания': 'Sherik | Korporativ xizmatlar bo\'limi boshlig\'i',
        'Основатель, Управляющий партнёр': 'Asoschi, Boshqaruvchi sherik',
        'Основатель, Партнёр, Профессор': 'Asoschi, Sherik, Professor',
        'Старший юрист': 'Advokat',
        'Юрист': 'Advokat',
        'Адвокат': 'Advokat',
        'Адвокат | Профессиональный медиатор': 'Advokat | Professional mediator',
        'Адвокат | Международный юрист': 'Advokat | Xalqaro yurist',
        'Адвокат | Финансовый юрист': 'Advokat | Moliyaviy yurist',
        'Финансовый юрист | Аудитор': 'Moliyaviy yurist | Auditor',
        'Младший юрист': 'Kichik yurist'
      },
      specMap: {
        'Киберправо': 'Kiberhuquq', 'IT-право': 'IT-huquq', 'Цифровое право': 'Raqamli huquq',
        'Экономические споры': 'Iqtisodiy nizolar', 'Корпоративное право': 'Korporativ huquq', 'M&A': 'M&A',
        'Регистрация бизнеса': "Biznesni ro'yxatga olish", 'Стартапы': 'Startaplar',
        'Контрактное право': 'Shartnoma huquqi', 'Банковское право': 'Bank huquqi', 'ВЭД': 'Tashqi savdo',
        'Налоговое право': 'Soliq huquqi', 'Финансовое право': 'Moliya huquqi', 'Аудит': 'Audit',
        'Уголовное право': 'Jinoiy huquq', 'Защита бизнеса': 'Biznesni himoyalash', 'Экономические преступления': 'Iqtisodiy jinoyatlar',
        'Трудовое право': 'Mehnat huquqi', 'HR-консалтинг': 'HR-konsalting', 'Миграционное право': 'Migratsiya huquqi',
        'Финтех': 'Fintech', 'Платёжные системы': "To'lov tizimlari",
        'Интеллектуальная собственность': 'Intellektual mulk', 'Авторское право': 'Mualliflik huquqi', 'Товарные знаки': 'Tovar belgilari',
        'Таможенное право': 'Bojxona huquqi', 'Логистика': 'Logistika',
        'Недвижимость': "Ko'chmas mulk", 'Строительство': 'Qurilish', 'Девелопмент': 'Development',
        'Медиация': 'Mediatsiya', 'Переговоры': 'Muzokaralar', 'Разрешение споров': 'Nizolarni hal etish',
        'Семейное право': 'Oila huquqi', 'Наследство': 'Meros', 'Личные активы': 'Shaxsiy aktivlar',
        'Государственные закупки': 'Davlat xaridlari', 'Тендеры': 'Tenderlar', 'Госконтракты': 'Davlat shartnomalari',
        'Экологическое право': 'Ekologiya huquqi', 'Промышленная безопасность': 'Sanoat xavfsizligi', 'Комплаенс': 'Komplaens',
        'Экономическое право': 'Iqtisodiy huquq',
        'Киберпреступления': 'Kiberjinoyatlar',
        'Космическое право': 'Kosmik huquq',
        'Бухгалтерский учёт и аудит': 'Buxgalteriya va audit',
        'Финансовые споры': 'Moliyaviy nizolar',
        'Административное право': 'Ma\'muriy huquq',
        'Инвестиционный арбитраж': 'Investitsion arbitraj',
        'Бизнес-право': 'Biznes huquqi',
        'Международное право': 'Xalqaro huquq',
        'Инвестиционное право': 'Investitsion huquq',
        'Международный арбитраж': 'Xalqaro arbitraj',
        'Гражданское право': 'Fuqarolik huquqi',
        'Коммерческое право': 'Tijorat huquqi'
      }
    },
    news: { sTag: 'Yangiliklar', sTitle: 'Huquq va texnologiyalar', sDesc: 'Kiberxavfsizlik, IT-huquq va yuridik dunyo haqidagi dolzarb yangiliklar — 2025', read: "Ko'proq o'qish →" },
    contact: {
      sTag: 'Aloqa', sTitle: "Biz bilan bog'laning", sDesc: 'Birinchi konsultatsiya — bepul. Bir soat ichida javob beramiz.',
      addr: 'Manzil', phone: 'Telefon', email: 'Email', formTitle: 'Savol berish',
      ph: { name: 'Ismingiz', tel: 'Telefon raqamingiz', email: 'Email (ixtiyoriy)', svc: 'Xizmatni tanlang', msg: 'Vaziyatingizni yoki savolingizni qisqacha tavsiflang...' },
      submit: "So'rov yuborish →", success: "✓ So'rovingiz yuborildi! Tez orada siz bilan bog'lanamiz.", error: "So'rovni yuborib bo'lmadi. Keyinroq urinib ko'ring yoki bizga qo'ng'iroq qiling.",
      svcOptions: ['Korporativ huquq va M&A','IT va kiberhuquq','Soliq amaliyoti','Bank va moliya huquqi','Mehnat huquqi','Intellektual mulk','Bojxona huquqi','Biznesni jinoiy himoyalash','Iqtisodiy nizolar','Boshqa']
    },
    footer: {
      rights: '© 2026 GSP LAW — Gulyamov, Sadikov and Partners. Barcha huquqlar himoyalangan.',
      sTitle: 'Xizmatlar', cTitle: 'Aloqa',
      servicesList: ['Korporativ huquq','IT va kiberhuquq','Soliq amaliyoti','Bank huquqi','Mehnat huquqi','Intellektual mulk']
    },
    lp: {
      back: 'Jamoaga qaytish', bio: 'Biografiya', help: 'Qanday yordam bera olaman', services: 'Xizmatlar',
      consultTitle: 'Konsultatsiyaga yozilish', sendBtn: "So'rov yuborish",
      expLbl: 'Ish tajribasi', casesLbl: 'Yakunlangan ishlar', firm: 'Firma', office: 'Ofis',
      blogTag: 'Blog', blogDesc: 'Ekspert maqolalar va tahlil', info: "Ma'lumot",
      educationTitle: "Ta'lim", achievementsTitle: 'Yutuqlar va mukofotlar', publicationsTitle: 'Nashrlar', certificatesTitle: 'Sertifikatlar va guvohnomalar',
      otherTag: 'Jamoa', otherTitle: 'Boshqa mutaxassislar', allTeam: 'Barcha jamoa →', readMore: "Ko'proq o'qish →",
      heroTag: 'GSP LAW FIRM mutaxassisi', visitWebsite: '🔗 Veb-sayt', notFound: 'Sahifa topilmadi'
    },
    casesPage: {
      heroTag: 'Bizning amaliyot', heroTitle: "G'alaba qozonilgan ishlar", heroDesc: 'Haqiqiy mijozlar uchun haqiqiy natijalar',
      challenge: 'Vazifa', approach: 'Bizning yondashuv', outcome: 'Natija',
      durationLabel: 'Davomiyligi', jurLabel: 'Yurisdiksiya', lawyerLabel: 'Advokat',
      filterAll: 'Barcha ishlar',
      backBtn: '← Bosh sahifaga'
    }
  },
  en: {
    nav: { about: 'About', services: 'Services', team: 'Team', cases: 'Cases', consult: 'Consultation', news: 'News' },
    stats: ['years of experience', 'case portfolio', 'attorneys', 'clients'],
    hero: {
      tag: 'Law Firm in Tashkent',
      desc: 'A specialized team of experts in IT law, corporate law, and economic dispute resolution',
      btn1: 'Our Team', btn2: 'Get Consultation'
    },
    about: {
      sTag: 'About GSP LAW FIRM', sTitle: 'Professionalism. Trust. Results.',
      p1: 'GSP LAW FIRM is a specialized law firm providing comprehensive legal support for IT businesses, startups, and commercial organizations in Uzbekistan and abroad.',
      p2: 'Our team brings together experienced lawyers with deep expertise in cyber law, corporate law, tax and banking legislation.',
      li: ['High professionalism','Individual approach to every client','Efficiency and clarity','Complete confidentiality'],
      mTitle: 'Our Mission', mText: "We put our clients' interests first, ensuring maximum protection of rights and legitimate interests in any legal situation.",
      yearsLabel: 'years',
      teamTag: 'Key Partners', teamTitle: 'Founders & Partners'
    },
    metrics: {
      sTag: 'Performance', sTitle: 'Effectiveness in Numbers', sDesc: 'Results that speak for themselves',
      winRate: 'Win Rate', portfolioVal: 'Portfolio Value', combinedExp: 'Combined Experience',
      intlCases: 'International Cases', satisfaction: 'Client Satisfaction', industries: 'Practice Industries',
      clients: 'Clients Served', yearsOnMkt: 'Years on Market', languages: 'Practice Languages', support: 'Client Support'
    },
    services: {
      sTag: 'Practice Areas', sTitle: 'Practice Areas', sDesc: 'Professional legal protection for your business across all key directions',
      items: [
        { title: 'Corporate Law & M&A', desc: 'M&A transaction support, corporate structuring, shareholder agreements' },
        { title: 'IT & Cyber Law', desc: 'Legal support for IT companies, startups, data protection and cybersecurity' },
        { title: 'Banking & Finance Law', desc: 'Regulatory matters, fintech, licensing, financial transactions' },
        { title: 'Tax Practice', desc: 'Tax planning, optimization, disputes with tax authorities' },
        { title: 'Economic Disputes', desc: 'Representation in arbitration courts, mediation, negotiations' },
        { title: 'Customs Law', desc: 'Foreign trade support, customs clearance, disputes with customs authorities' },
        { title: 'Criminal Business Defense', desc: 'Defense of entrepreneurs and executives in criminal cases' },
        { title: 'Labor Law', desc: 'Employment contracts, employee disputes, HR administration' },
        { title: 'Intellectual Property', desc: 'Trademark registration, patents, copyright protection' },
        { title: 'Ongoing Legal Service', desc: 'Comprehensive ongoing legal support for commercial organizations' },
        { title: 'Contract Law', desc: 'Contract drafting and review, negotiations, dispute resolution' },
        { title: 'Real Estate', desc: 'Real estate transactions, development projects, lease disputes' }
      ]
    },
    cases: {
      sTag: 'Cases', sTitle: 'Cases Won', sDesc: 'Real results we have achieved for our clients', result: 'Result', year: 'Year', lawyer: 'Attorney',
      allCasesBtn: 'All Cases →'
    },
    lawyers: {
      sTag: 'Team', sTitle: 'Our Attorneys & Lawyers', sDesc: 'Each specialist has deep expertise in their area of law and real-world experience', exp: 'experience', casesLbl: 'cases', more: 'View Profile →',
      titleMap: {
        'Партнёр, Профессор': 'Partner, Professor',
        'Управляющий партнёр': 'Managing Partner',
        'Партнёр, Корпоративный юрист': 'Partner, Corporate Lawyer',
        'Партнёр, Специалист по контрактам': 'Partner, Contract Specialist',
        'Партнёр | Руководитель отдела корпоративного обслуживания': 'Partner | Head of Corporate Services',
        'Основатель, Управляющий партнёр': 'Founder, Managing Partner',
        'Основатель, Партнёр, Профессор': 'Founder, Partner, Professor',
        'Старший юрист': 'Advocate',
        'Юрист': 'Advocate',
        'Адвокат': 'Advocate',
        'Адвокат | Профессиональный медиатор': 'Advocate | Professional Mediator',
        'Адвокат | Международный юрист': 'Advocate | International Lawyer',
        'Адвокат | Финансовый юрист': 'Advocate | Financial Lawyer',
        'Финансовый юрист | Аудитор': 'Financial Lawyer | Auditor',
        'Младший юрист': 'Junior Lawyer'
      },
      specMap: {
        'Киберправо': 'Cyber Law', 'IT-право': 'IT Law', 'Цифровое право': 'Digital Law',
        'Экономические споры': 'Economic Disputes', 'Корпоративное право': 'Corporate Law', 'M&A': 'M&A',
        'Регистрация бизнеса': 'Business Registration', 'Стартапы': 'Startups',
        'Контрактное право': 'Contract Law', 'Банковское право': 'Banking Law', 'ВЭД': 'Foreign Trade',
        'Налоговое право': 'Tax Law', 'Финансовое право': 'Financial Law', 'Аудит': 'Audit',
        'Уголовное право': 'Criminal Law', 'Защита бизнеса': 'Business Defense', 'Экономические преступления': 'Economic Crimes',
        'Трудовое право': 'Labor Law', 'HR-консалтинг': 'HR Consulting', 'Миграционное право': 'Immigration Law',
        'Финтех': 'Fintech', 'Платёжные системы': 'Payment Systems',
        'Интеллектуальная собственность': 'Intellectual Property', 'Авторское право': 'Copyright', 'Товарные знаки': 'Trademarks',
        'Таможенное право': 'Customs Law', 'Логистика': 'Logistics',
        'Недвижимость': 'Real Estate', 'Строительство': 'Construction', 'Девелопмент': 'Development',
        'Медиация': 'Mediation', 'Переговоры': 'Negotiations', 'Разрешение споров': 'Dispute Resolution',
        'Семейное право': 'Family Law', 'Наследство': 'Inheritance', 'Личные активы': 'Personal Assets',
        'Государственные закупки': 'Public Procurement', 'Тендеры': 'Tenders', 'Госконтракты': 'Government Contracts',
        'Экологическое право': 'Environmental Law', 'Промышленная безопасность': 'Industrial Safety', 'Комплаенс': 'Compliance',
        'Экономическое право': 'Economic Law',
        'Киберпреступления': 'Cybercrime',
        'Космическое право': 'Space Law',
        'Бухгалтерский учёт и аудит': 'Accounting & Audit',
        'Финансовые споры': 'Financial Disputes',
        'Административное право': 'Administrative Law',
        'Инвестиционный арбитраж': 'Investment Arbitration',
        'Бизнес-право': 'Business Law',
        'Международное право': 'International Law',
        'Инвестиционное право': 'Investment Law',
        'Международный арбитраж': 'International Arbitration',
        'Гражданское право': 'Civil Law',
        'Коммерческое право': 'Commercial Law'
      }
    },
    news: { sTag: 'News', sTitle: 'Law & Technology', sDesc: 'Latest news on cybersecurity, IT law, and the legal world — 2025', read: 'Read more →' },
    contact: {
      sTag: 'Contact', sTitle: 'Get In Touch', sDesc: "First consultation is free. We'll respond within one hour.",
      addr: 'Address', phone: 'Phone', email: 'Email', formTitle: 'Ask a Question',
      ph: { name: 'Your Name', tel: 'Phone Number', email: 'Email (optional)', svc: 'Select a service', msg: 'Briefly describe your situation or question...' },
      submit: 'Send Request →', success: '✓ Request sent! We will contact you shortly.', error: 'Failed to send request. Please try again later or call us.',
      svcOptions: ['Corporate Law & M&A','IT & Cyber Law','Tax Practice','Banking & Finance Law','Labor Law','Intellectual Property','Customs Law','Criminal Business Defense','Economic Disputes','Other']
    },
    footer: {
      rights: '© 2026 GSP LAW — Gulyamov, Sadikov and Partners. All rights reserved.',
      sTitle: 'Services', cTitle: 'Contact',
      servicesList: ['Corporate Law','IT & Cyber Law','Tax Practice','Banking Law','Labor Law','Intellectual Property']
    },
    lp: {
      back: 'Back to Team', bio: 'Biography', help: 'How I Can Help', services: 'Services',
      consultTitle: 'Book a Consultation', sendBtn: 'Send Request',
      expLbl: 'Experience', casesLbl: 'Cases Completed', firm: 'Firm', office: 'Office',
      blogTag: 'Blog', blogDesc: 'Expert articles and analysis', info: 'Information',
      educationTitle: 'Education', achievementsTitle: 'Achievements & Awards', publicationsTitle: 'Publications', certificatesTitle: 'Certificates & Credentials',
      otherTag: 'Team', otherTitle: 'Other Specialists', allTeam: 'Full Team →', readMore: 'Read more →',
      heroTag: 'GSP LAW FIRM Specialist', visitWebsite: '🔗 Visit Website', notFound: 'Page Not Found'
    },
    casesPage: {
      heroTag: 'Our Practice', heroTitle: 'Cases Won', heroDesc: 'Real results for real clients',
      challenge: 'Challenge', approach: 'Our Approach', outcome: 'Outcome',
      durationLabel: 'Duration', jurLabel: 'Jurisdiction', lawyerLabel: 'Attorney',
      filterAll: 'All Cases',
      backBtn: '← Back to Home'
    }
  }
};
