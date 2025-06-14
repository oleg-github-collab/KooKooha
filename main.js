// Kookooha - Mental Health & Corporate Culture Website
// Enhanced JavaScript with Full Localization

// Global variables
let currentLanguage = 'en';
let isNavMenuOpen = false;
let heroChart, aiChart;
let stripe;

// Complete translations object
const translations = {
    en: {
        // Navigation
        'nav.home': 'Home',
        'nav.about': 'About',
        'nav.services': 'Services',
        'nav.product': 'AI Product',
        'nav.clients': 'Clients',
        'nav.calculator': 'Calculator',
        'nav.contact': 'Contact',
        
        // Hero Section
        'hero.badge': 'Protecting Mental Health',
        'hero.title': 'Transform Your Workplace Into a Mental Health Haven',
        'hero.subtitle': 'Harness the power of advanced analytics and AI to create environments where employees don\'t just work—they thrive, innovate, and find genuine fulfillment.',
        'hero.description': 'Join forward-thinking organizations worldwide who are revolutionizing workplace wellness. Our data-driven approach has helped companies reduce burnout by 67%, increase productivity by 45%, and create cultures where mental health is not an afterthought, but a cornerstone of success.',
        'hero.stat1': 'Client Satisfaction',
        'hero.stat2': 'Companies Transformed',
        'hero.stat3': 'Productivity Increase',
        'hero.cta1': 'Start Your Transformation',
        'hero.cta2': 'Watch Demo',
        
        // About Section
        'about.title': 'Why Mental Health Matters in Your Workplace',
        'about.subtitle': 'The cost of ignoring employee mental health is measured not just in dollars, but in human potential lost.',
        'about.heading': 'The Silent Crisis in Modern Workplaces',
        'about.text1': 'Every day, millions of talented professionals operate at a fraction of their potential, not due to lack of skills or motivation, but because of unaddressed mental health challenges. Stress, burnout, and disengagement have become the norm rather than the exception.',
        'about.text2': 'At Kookooha, we believe that exceptional performance and employee wellbeing are not mutually exclusive—they\'re intrinsically linked. Our mission is to help organizations unlock their true potential by creating psychologically safe, supportive environments where innovation flourishes and people love coming to work.',
        'about.feature1.title': 'Data-Driven Insights',
        'about.feature1.desc': 'Transform raw data into actionable strategies that improve both performance and wellbeing.',
        'about.feature2.title': 'Human-Centered Approach',
        'about.feature2.desc': 'Technology serves people, not the other way around. Every solution is designed with empathy.',
        'about.feature3.title': 'Preventive Care',
        'about.feature3.desc': 'Identify and address issues before they become crises, saving costs and careers.',
        'about.impact1.title': 'Reduce Burnout',
        'about.impact1.desc': '67% reduction in employee burnout rates within 6 months',
        'about.impact2.title': 'Boost Engagement',
        'about.impact2.desc': '82% increase in employee engagement scores',
        'about.impact3.title': 'Save Costs',
        'about.impact3.desc': '€2.5M average savings from reduced turnover',
        'about.impact4.title': 'Retain Talent',
        'about.impact4.desc': '91% talent retention rate after implementation',
        
        // Services Section
        'services.title': 'Comprehensive Mental Health Solutions',
        'services.subtitle': 'From assessment to transformation, we provide end-to-end solutions tailored to your organization\'s unique needs.',
        'services.assessment.title': 'Deep Workplace Assessment',
        'services.assessment.desc': 'Our proprietary assessment methodology combines psychometric testing, behavioral analytics, and cultural mapping to provide a 360-degree view of your workplace mental health landscape. Understand not just where you are, but why you\'re there.',
        'services.assessment.feature1': 'Comprehensive sociometric analysis',
        'services.assessment.feature2': 'Team dynamics evaluation',
        'services.assessment.feature3': 'Stress point identification',
        'services.assessment.feature4': 'Cultural health scoring',
        'services.monitoring.title': '24/7 Mental Health Monitoring',
        'services.monitoring.desc': 'Real-time monitoring that respects privacy while providing crucial insights. Our AI-powered platform continuously analyzes workplace indicators, alerting you to potential issues before they escalate into crises.',
        'services.monitoring.feature1': 'Anonymous mood tracking',
        'services.monitoring.feature2': 'Predictive burnout alerts',
        'services.monitoring.feature3': 'Team wellness dashboards',
        'services.monitoring.feature4': 'Automated intervention triggers',
        'services.facilitation.title': 'Culture Transformation Programs',
        'services.facilitation.desc': 'Building a mentally healthy workplace isn\'t a one-time project—it\'s an ongoing journey. Our expert facilitators guide your organization through sustainable transformation, embedding wellness into your company DNA.',
        'services.facilitation.feature1': 'Leadership coaching',
        'services.facilitation.feature2': 'Team building workshops',
        'services.facilitation.feature3': 'Policy development',
        'services.facilitation.feature4': 'Change management support',
        'services.learnmore': 'Learn More',
        'services.cta.title': 'Ready to transform your workplace?',
        'services.cta.desc': 'Join hundreds of companies creating mentally healthy, high-performing cultures.',
        'services.cta.button': 'Calculate Your Investment',
        
        // AI Product Section
        'ai.badge': 'Coming Q2 2025',
        'ai.title': 'Introducing Human Lens AI',
        'ai.subtitle': 'The future of workplace intelligence is here. Continuous sociometric testing meets advanced AI.',
        'ai.headline': 'Revolutionary Workplace Intelligence Platform',
        'ai.description1': 'Human Lens AI represents a quantum leap in organizational psychology. By combining continuous sociometric testing with advanced machine learning, we\'ve created a platform that doesn\'t just monitor—it predicts, prevents, and prescribes solutions for workplace mental health challenges.',
        'ai.description2': 'Imagine knowing exactly which teams are struggling before they burn out. Picture having AI-generated recommendations that actually work because they\'re based on your organization\'s unique culture and dynamics. That\'s the power of Human Lens AI.',
        'ai.feature1.title': 'Continuous Sociometric Analysis',
        'ai.feature1.desc': 'Map team dynamics and communication patterns in real-time, identifying bottlenecks and collaboration opportunities.',
        'ai.feature2.title': 'Predictive AI Models',
        'ai.feature2.desc': 'Machine learning algorithms that predict burnout, turnover risk, and team conflicts weeks before they manifest.',
        'ai.feature3.title': 'Automated Interventions',
        'ai.feature3.desc': 'Smart recommendations and automated wellness programs triggered by AI-detected patterns and anomalies.',
        'ai.feature4.title': 'Privacy-First Design',
        'ai.feature4.desc': 'Advanced encryption and anonymization ensure complete privacy while delivering actionable insights.',
        'ai.waitlist.title': 'Be Among the First to Experience Human Lens AI',
        'ai.waitlist.desc': 'Join our exclusive early access program and shape the future of workplace wellness.',
        'ai.waitlist.button': 'Join Waitlist',
        
        // Clients Section
        'clients.title': 'Trusted by Leading Organizations',
        'clients.subtitle': 'From startups to Fortune 500 companies, we\'re helping organizations worldwide create mentally healthy workplaces.',
        'clients.testimonial1.text': 'Kookooha transformed our workplace culture. Employee satisfaction is at an all-time high, and we\'ve seen a 45% reduction in turnover. The ROI has been incredible.',
        'clients.testimonial1.name': 'Sarah Klein',
        'clients.testimonial1.position': 'CHRO, TechCorp',
        'clients.testimonial2.text': 'The insights from Kookooha\'s platform helped us identify and address burnout risks before they became critical. Our teams are more engaged and productive than ever.',
        'clients.testimonial2.name': 'Michael Rodriguez',
        'clients.testimonial2.position': 'CEO, InnovateLab',
        
        // Calculator Section
        'calc.title': 'Calculate Your Investment in Mental Health',
        'calc.subtitle': 'Transparent pricing for transformative results. See exactly what your investment will be.',
        'calc.people.label': 'Number of Employees',
        'calc.criteria.label': 'Research Criteria',
        'calc.breakdown.title': 'Price Breakdown',
        'calc.breakdown.base': 'Base Package (4 people, 2 criteria)',
        'calc.breakdown.people': 'Additional People',
        'calc.breakdown.criteria': 'Additional Criteria',
        'calc.total.label': 'Total Investment',
        'calc.total.note': 'One-time comprehensive assessment',
        'calc.benefits.title': 'What You Get:',
        'calc.benefits.item1': 'Complete sociometric and adaptometric testing',
        'calc.benefits.item2': 'Detailed analytics and infographics',
        'calc.benefits.item3': 'Team dynamics visualization',
        'calc.benefits.item4': 'Actionable recommendations report',
        'calc.benefits.item5': '3-month follow-up consultation',
        'calc.checkout': 'Secure Checkout',
        'calc.security': '256-bit SSL encryption • PCI compliant',
        
        // Contact Section
        'contact.title': 'Let\'s Transform Your Workplace Together',
        'contact.subtitle': 'Have questions? Ready to start? We\'re here to help you create a mentally healthy workplace.',
        'contact.form.firstname': 'First Name',
        'contact.form.lastname': 'Last Name',
        'contact.form.email': 'Email Address',
        'contact.form.phone': 'Phone Number',
        'contact.form.company': 'Company Name',
        'contact.form.employees': 'Number of Employees',
        'contact.form.interest': 'What are you interested in?',
        'contact.form.message': 'Tell us about your challenges',
        'contact.form.submit': 'Send Message',
        'contact.info.offices': 'Our Offices',
        'contact.info.phone': 'Phone',
        'contact.info.email': 'Email',
        'contact.info.hours': 'Business Hours',
        
        // Footer
        'footer.about': 'Transforming workplaces worldwide through data-driven mental health solutions. Creating environments where employees thrive, not just survive.',
        'footer.solutions': 'Solutions',
        'footer.solutions.assessment': 'Workplace Assessment',
        'footer.solutions.monitoring': 'Mental Health Monitoring',
        'footer.solutions.transformation': 'Culture Transformation',
        'footer.solutions.ai': 'Human Lens AI',
        'footer.company': 'Company',
        'footer.company.about': 'About Us',
        'footer.company.careers': 'Careers',
        'footer.resources': 'Resources',
        'footer.resources.blog': 'Blog',
        'footer.resources.support': 'Support Center',
        'footer.newsletter': 'Stay Updated',
        'footer.newsletter.desc': 'Get the latest insights on workplace mental health delivered to your inbox.',
        'footer.privacy': 'Privacy Policy',
        'footer.terms': 'Terms of Service',
        
        // Notifications
        'notification.contact.success': 'Message sent successfully! We\'ll get back to you soon.',
        'notification.waitlist.success': 'Successfully joined the waitlist! You\'ll be notified when Human Lens AI launches.',
        'notification.newsletter.success': 'Successfully subscribed to newsletter!',
        'notification.email.invalid': 'Please enter a valid email address.',
        'notification.checkout.processing': 'Redirecting to secure checkout...'
    },
    
    de: {
        // Navigation
        'nav.home': 'Startseite',
        'nav.about': 'Über uns',
        'nav.services': 'Leistungen',
        'nav.product': 'KI-Produkt',
        'nav.clients': 'Kunden',
        'nav.calculator': 'Rechner',
        'nav.contact': 'Kontakt',
        
        // Hero Section
        'hero.badge': 'Mentale Gesundheit schützen',
        'hero.title': 'Verwandeln Sie Ihren Arbeitsplatz in eine Oase der mentalen Gesundheit',
        'hero.subtitle': 'Nutzen Sie die Kraft fortschrittlicher Analytik und KI, um Umgebungen zu schaffen, in denen Mitarbeiter nicht nur arbeiten—sie gedeihen, innovieren und finden echte Erfüllung.',
        'hero.description': 'Schließen Sie sich zukunftsorientierten Organisationen weltweit an, die das Wohlbefinden am Arbeitsplatz revolutionieren. Unser datengetriebener Ansatz hat Unternehmen geholfen, Burnout um 67% zu reduzieren, die Produktivität um 45% zu steigern und Kulturen zu schaffen, in denen mentale Gesundheit kein nachträglicher Gedanke ist, sondern ein Eckpfeiler des Erfolgs.',
        'hero.stat1': 'Kundenzufriedenheit',
        'hero.stat2': 'Transformierte Unternehmen',
        'hero.stat3': 'Produktivitätssteigerung',
        'hero.cta1': 'Starten Sie Ihre Transformation',
        'hero.cta2': 'Demo ansehen',
        
        // About Section
        'about.title': 'Warum mentale Gesundheit in Ihrem Arbeitsplatz wichtig ist',
        'about.subtitle': 'Die Kosten für das Ignorieren der psychischen Gesundheit der Mitarbeiter werden nicht nur in Euro gemessen, sondern auch in verlorenem menschlichem Potenzial.',
        'about.heading': 'Die stille Krise in modernen Arbeitsplätzen',
        'about.text1': 'Jeden Tag arbeiten Millionen talentierter Fachkräfte nur mit einem Bruchteil ihres Potenzials, nicht aufgrund mangelnder Fähigkeiten oder Motivation, sondern wegen ungelöster Herausforderungen der psychischen Gesundheit. Stress, Burnout und Desengagement sind zur Norm geworden.',
        'about.text2': 'Bei Kookooha glauben wir, dass außergewöhnliche Leistung und Mitarbeiterwohlbefinden sich nicht ausschließen—sie sind untrennbar miteinander verbunden. Unsere Mission ist es, Organisationen dabei zu helfen, ihr wahres Potenzial zu entfalten, indem wir psychologisch sichere, unterstützende Umgebungen schaffen.',
        'about.feature1.title': 'Datengesteuerte Erkenntnisse',
        'about.feature1.desc': 'Verwandeln Sie Rohdaten in umsetzbare Strategien, die sowohl Leistung als auch Wohlbefinden verbessern.',
        'about.feature2.title': 'Menschenzentrierter Ansatz',
        'about.feature2.desc': 'Technologie dient den Menschen, nicht umgekehrt. Jede Lösung wird mit Empathie entwickelt.',
        'about.feature3.title': 'Präventive Pflege',
        'about.feature3.desc': 'Identifizieren und lösen Sie Probleme, bevor sie zu Krisen werden, und sparen Sie Kosten und Karrieren.',
        'about.impact1.title': 'Burnout reduzieren',
        'about.impact1.desc': '67% Reduktion der Mitarbeiter-Burnout-Raten innerhalb von 6 Monaten',
        'about.impact2.title': 'Engagement steigern',
        'about.impact2.desc': '82% Steigerung der Mitarbeiterengagement-Werte',
        'about.impact3.title': 'Kosten sparen',
        'about.impact3.desc': '€2,5M durchschnittliche Einsparungen durch reduzierte Fluktuation',
        'about.impact4.title': 'Talente halten',
        'about.impact4.desc': '91% Talentbindungsrate nach Implementierung',
        
        // Services Section
        'services.title': 'Umfassende Mental Health Lösungen',
        'services.subtitle': 'Von der Bewertung bis zur Transformation bieten wir End-to-End-Lösungen, die auf die einzigartigen Bedürfnisse Ihrer Organisation zugeschnitten sind.',
        'services.assessment.title': 'Tiefgreifende Arbeitsplatz-Bewertung',
        'services.assessment.desc': 'Unsere proprietäre Bewertungsmethodik kombiniert psychometrische Tests, Verhaltensanalytik und kulturelle Kartierung, um einen 360-Grad-Blick auf Ihre Arbeitsplatz-Mental-Health-Landschaft zu bieten.',
        'services.assessment.feature1': 'Umfassende soziometrische Analyse',
        'services.assessment.feature2': 'Bewertung der Teamdynamik',
        'services.assessment.feature3': 'Identifikation von Stresspunkten',
        'services.assessment.feature4': 'Kulturelle Gesundheitsbewertung',
        'services.monitoring.title': '24/7 Mental Health Monitoring',
        'services.monitoring.desc': 'Echtzeit-Überwachung, die die Privatsphäre respektiert und gleichzeitig wichtige Erkenntnisse liefert. Unsere KI-gestützte Plattform analysiert kontinuierlich Arbeitsplatzindikatoren.',
        'services.monitoring.feature1': 'Anonymes Stimmungstracking',
        'services.monitoring.feature2': 'Vorhersagende Burnout-Warnungen',
        'services.monitoring.feature3': 'Team-Wellness-Dashboards',
        'services.monitoring.feature4': 'Automatisierte Interventionsauslöser',
        'services.facilitation.title': 'Kulturtransformationsprogramme',
        'services.facilitation.desc': 'Der Aufbau eines mental gesunden Arbeitsplatzes ist kein einmaliges Projekt—es ist eine fortlaufende Reise. Unsere Experten führen Ihre Organisation durch nachhaltige Transformation.',
        'services.facilitation.feature1': 'Führungscoaching',
        'services.facilitation.feature2': 'Teambuilding-Workshops',
        'services.facilitation.feature3': 'Richtlinienentwicklung',
        'services.facilitation.feature4': 'Change-Management-Unterstützung',
        'services.learnmore': 'Mehr erfahren',
        'services.cta.title': 'Bereit, Ihren Arbeitsplatz zu transformieren?',
        'services.cta.desc': 'Schließen Sie sich Hunderten von Unternehmen an, die mental gesunde, leistungsstarke Kulturen schaffen.',
        'services.cta.button': 'Ihre Investition berechnen',
        
        // Calculator Section
        'calc.title': 'Berechnen Sie Ihre Investition in mentale Gesundheit',
        'calc.subtitle': 'Transparente Preise für transformative Ergebnisse. Sehen Sie genau, was Ihre Investition sein wird.',
        'calc.people.label': 'Anzahl der Mitarbeiter',
        'calc.criteria.label': 'Forschungskriterien',
        'calc.breakdown.title': 'Preisaufschlüsselung',
        'calc.breakdown.base': 'Basispaket (4 Personen, 2 Kriterien)',
        'calc.breakdown.people': 'Zusätzliche Personen',
        'calc.breakdown.criteria': 'Zusätzliche Kriterien',
        'calc.total.label': 'Gesamtinvestition',
        'calc.total.note': 'Einmalige umfassende Bewertung',
        'calc.benefits.title': 'Was Sie erhalten:',
        'calc.benefits.item1': 'Vollständige soziometrische und adaptometrische Tests',
        'calc.benefits.item2': 'Detaillierte Analytik und Infografiken',
        'calc.benefits.item3': 'Visualisierung der Teamdynamik',
        'calc.benefits.item4': 'Umsetzbare Empfehlungsberichte',
        'calc.benefits.item5': '3-monatige Nachberatung',
        'calc.checkout': 'Sichere Zahlung',
        'calc.security': '256-Bit SSL-Verschlüsselung • PCI-konform',
        
        // Footer and other sections...
        'footer.about': 'Arbeitsplätze weltweit durch datengesteuerte Mental-Health-Lösungen transformieren. Umgebungen schaffen, in denen Mitarbeiter gedeihen, nicht nur überleben.',
        'footer.solutions': 'Lösungen',
        'footer.solutions.assessment': 'Arbeitsplatzbewertung',
        'footer.solutions.monitoring': 'Mental Health Monitoring',
        'footer.solutions.transformation': 'Kulturtransformation',
        'footer.solutions.ai': 'Human Lens KI',
        'footer.company': 'Unternehmen',
        'footer.company.about': 'Über uns',
        'footer.company.careers': 'Karriere',
        'footer.resources': 'Ressourcen',
        'footer.resources.blog': 'Blog',
        'footer.resources.support': 'Support-Center',
        'footer.newsletter': 'Bleiben Sie auf dem Laufenden',
        'footer.newsletter.desc': 'Erhalten Sie die neuesten Erkenntnisse zur Arbeitsplatz-Mental-Health in Ihrem Posteingang.',
        'footer.privacy': 'Datenschutzrichtlinie',
        'footer.terms': 'Nutzungsbedingungen'
    },
    
    uk: {
        // Navigation
        'nav.home': 'Головна',
        'nav.about': 'Про нас',
        'nav.services': 'Послуги',
        'nav.product': 'ШІ Продукт',
        'nav.clients': 'Клієнти',
        'nav.calculator': 'Калькулятор',
        'nav.contact': 'Контакти',
        
        // Hero Section
        'hero.badge': 'Захист психічного здоров\'я',
        'hero.title': 'Перетворіть своє робоче місце на притулок психічного здоров\'я',
        'hero.subtitle': 'Використовуйте силу передової аналітики та ШІ для створення середовищ, де співробітники не просто працюють—вони процвітають, інновують та знаходять справжнє задоволення.',
        'hero.description': 'Приєднуйтесь до передових організацій по всьому світу, які революціонізують благополуччя на робочому місці. Наш підхід, заснований на даних, допоміг компаніям зменшити вигорання на 67%, підвищити продуктивність на 45% та створити культури, де психічне здоров\'я не є додатковою думкою, а наріжним каменем успіху.',
        'hero.stat1': 'Задоволеність клієнтів',
        'hero.stat2': 'Трансформовані компанії',
        'hero.stat3': 'Зростання продуктивності',
        'hero.cta1': 'Почніть свою трансформацію',
        'hero.cta2': 'Дивитися демо',
        
        // About Section
        'about.title': 'Чому психічне здоров\'я важливе на вашому робочому місці',
        'about.subtitle': 'Вартість ігнорування психічного здоров\'я співробітників вимірюється не лише в гривнях, але й у втраченому людському потенціалі.',
        'about.heading': 'Тиха криза на сучасних робочих місцях',
        'about.text1': 'Щодня мільйони талановитих професіоналів працюють лише на частку свого потенціалу, не через брак навичок чи мотивації, а через невирішені проблеми психічного здоров\'я. Стрес, вигорання та відчуження стали нормою.',
        'about.text2': 'У Kookooha ми віримо, що виняткова продуктивність та благополуччя співробітників не є взаємовиключними—вони нерозривно пов\'язані. Наша місія—допомогти організаціям розкрити свій справжній потенціал, створюючи психологічно безпечні, підтримуючі середовища.',
        'about.feature1.title': 'Аналітика на основі даних',
        'about.feature1.desc': 'Перетворюйте сирі дані в практичні стратегії, які покращують як продуктивність, так і благополуччя.',
        'about.feature2.title': 'Людиноцентричний підхід',
        'about.feature2.desc': 'Технології служать людям, а не навпаки. Кожне рішення розроблене з емпатією.',
        'about.feature3.title': 'Превентивний догляд',
        'about.feature3.desc': 'Виявляйте та вирішуйте проблеми до того, як вони стануть кризами, економлячи витрати та кар\'єри.',
        'about.impact1.title': 'Зменшити вигорання',
        'about.impact1.desc': '67% зниження рівня вигорання співробітників протягом 6 місяців',
        'about.impact2.title': 'Підвищити залученість',
        'about.impact2.desc': '82% зростання показників залученості співробітників',
        'about.impact3.title': 'Заощадити кошти',
        'about.impact3.desc': '€2.5М середня економія від зниженої плинності кадрів',
        'about.impact4.title': 'Утримати таланти',
        'about.impact4.desc': '91% утримання талантів після впровадження',
        
        // Continue with other sections...
        'footer.about': 'Трансформуємо робочі місця по всьому світу через рішення психічного здоров\'я на основі даних. Створюємо середовища, де співробітники процвітають, а не просто виживають.',
        'footer.solutions': 'Рішення',
        'footer.solutions.assessment': 'Оцінка робочого місця',
        'footer.solutions.monitoring': 'Моніторинг психічного здоров\'я',
        'footer.solutions.transformation': 'Трансформація культури',
        'footer.solutions.ai': 'Human Lens ШІ',
        'footer.company': 'Компанія',
        'footer.company.about': 'Про нас',
        'footer.company.careers': 'Кар\'єра',
        'footer.resources': 'Ресурси',
        'footer.resources.blog': 'Блог',
        'footer.resources.support': 'Центр підтримки',
        'footer.newsletter': 'Залишайтесь в курсі',
        'footer.newsletter.desc': 'Отримуйте останні інсайти про психічне здоров\'я на робочому місці у свою скриньку.',
        'footer.privacy': 'Політика конфіденційності',
        'footer.terms': 'Умови використання'
    }
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeWebsite();
});

// Initialize all website functionality
function initializeWebsite() {
    hidePreloader();
    initializeNavigation();
    initializeScrollAnimations();
    initializeHeroSection();
    initializeCalculator();
    initializeCharts();
    initializeParticleSystem();
    initializeClientsCarousel();
    initializeLanguageSelector();
    initializeForms();
    initializeModals();
    initializeTooltips();
    initializeStripe();
    addTestimonialPhotos();
    initializeFooterFunctionality();
    
    // Initialize smooth scrolling
    initializeSmoothScrolling();
    
    // Event listeners
    window.addEventListener('resize', debounce(handleResize, 250));
    window.addEventListener('scroll', throttle(handleScroll, 16));
}

// Enhanced Language System
function initializeLanguageSelector() {
    const langButtons = document.querySelectorAll('.lang-btn');
    
    // Set initial language from localStorage or default to 'en'
    const savedLanguage = localStorage.getItem('kookooha-language') || 'en';
    changeLanguage(savedLanguage);
    
    langButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const lang = button.getAttribute('data-lang');
            changeLanguage(lang);
        });
    });
}

function changeLanguage(lang) {
    if (!translations[lang]) return;
    
    currentLanguage = lang;
    localStorage.setItem('kookooha-language', lang);
    
    // Update active button
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-lang') === lang) {
            btn.classList.add('active');
        }
    });
    
    // Update all translatable elements
    updateAllTranslations(lang);
    
    // Update form placeholders
    updateFormPlaceholders(lang);
    
    // Update select options
    updateSelectOptions(lang);
}

function updateAllTranslations(lang) {
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            // Check if element is input placeholder
            if (element.tagName === 'INPUT' && element.hasAttribute('placeholder')) {
                element.placeholder = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });
}

function updateFormPlaceholders(lang) {
    const placeholders = {
        en: {
            'your@email.com': 'your@email.com',
            'What mental health challenges is your organization facing?': 'What mental health challenges is your organization facing?'
        },
        de: {
            'your@email.com': 'ihre@email.de',
            'What mental health challenges is your organization facing?': 'Welche mentalen Gesundheitsherausforderungen hat Ihre Organisation?'
        },
        uk: {
            'your@email.com': 'ваша@пошта.com',
            'What mental health challenges is your organization facing?': 'З якими викликами психічного здоров\'я стикається ваша організація?'
        }
    };

    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(element => {
        const currentPlaceholder = element.placeholder;
        if (placeholders[lang][currentPlaceholder]) {
            element.placeholder = placeholders[lang][currentPlaceholder];
        }
    });
}

function updateSelectOptions(lang) {
    const selectOptions = {
        en: {
            'Select range': 'Select range',
            'Select service': 'Select service',
            'Workplace Assessment': 'Workplace Assessment',
            '24/7 Monitoring': '24/7 Monitoring',
            'Culture Transformation': 'Culture Transformation',
            'Human Lens AI': 'Human Lens AI',
            'Complete Solution': 'Complete Solution'
        },
        de: {
            'Select range': 'Bereich auswählen',
            'Select service': 'Service auswählen',
            'Workplace Assessment': 'Arbeitsplatzbewertung',
            '24/7 Monitoring': '24/7 Überwachung',
            'Culture Transformation': 'Kulturtransformation',
            'Human Lens AI': 'Human Lens KI',
            'Complete Solution': 'Komplettlösung'
        },
        uk: {
            'Select range': 'Виберіть діапазон',
            'Select service': 'Виберіть послугу',
            'Workplace Assessment': 'Оцінка робочого місця',
            '24/7 Monitoring': '24/7 Моніторинг',
            'Culture Transformation': 'Трансформація культури',
            'Human Lens AI': 'Human Lens ШІ',
            'Complete Solution': 'Повне рішення'
        }
    };

    document.querySelectorAll('select option').forEach(option => {
        const currentText = option.textContent;
        if (selectOptions[lang][currentText]) {
            option.textContent = selectOptions[lang][currentText];
        }
    });
}

// Add testimonial photos
function addTestimonialPhotos() {
    const testimonials = [
        {
            selector: '.testimonial-card:first-child .testimonial-author img',
            photo: 'https://images.unsplash.com/photo-1494790108755-2616b612b47c?w=120&h=120&fit=crop&crop=face&auto=format'
        },
        {
            selector: '.testimonial-card:last-child .testimonial-author img',
            photo: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=120&h=120&fit=crop&crop=face&auto=format'
        }
    ];

    testimonials.forEach(testimonial => {
        const img = document.querySelector(testimonial.selector);
        if (img) {
            img.src = testimonial.photo;
            img.alt = 'Testimonial photo';
        }
    });
}

// Enhanced Footer Functionality
function initializeFooterFunctionality() {
    // Remove social links
    const socialLinks = document.querySelector('.social-links');
    if (socialLinks) {
        socialLinks.remove();
    }
    
    // Implement footer button functionality
    const footerButtons = {
        'careers': () => showModal('careers'),
        'blog': () => showModal('blog'),
        'support': () => showModal('support'),
        'privacy': () => showModal('privacy'),
        'terms': () => showModal('terms')
    };
    
    Object.keys(footerButtons).forEach(buttonType => {
        const buttons = document.querySelectorAll(`[onclick*="${buttonType}"]`);
        buttons.forEach(button => {
            button.removeAttribute('onclick');
            button.addEventListener('click', (e) => {
                e.preventDefault();
                footerButtons[buttonType]();
            });
        });
    });
}

// Enhanced Modal System
function showModal(type) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalBody) return;
    
    const content = getModalContent(type);
    modalBody.innerHTML = content;
    
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function getModalContent(type) {
    const contents = {
        careers: `
            <h2>Join Our Team</h2>
            <p>We're looking for passionate individuals who want to make a difference in workplace mental health.</p>
            <div style="margin: 2rem 0;">
                <h3>Current Openings:</h3>
                <ul style="list-style: none; padding: 0;">
                    <li style="padding: 1rem; margin: 0.5rem 0; background: rgba(255,255,255,0.05); border-radius: 10px;">
                        <strong>Senior Data Scientist</strong><br>
                        <small>Berlin • Full-time • €80-120k</small>
                    </li>
                    <li style="padding: 1rem; margin: 0.5rem 0; background: rgba(255,255,255,0.05); border-radius: 10px;">
                        <strong>UX/UI Designer</strong><br>
                        <small>Remote • Full-time • €60-90k</small>
                    </li>
                    <li style="padding: 1rem; margin: 0.5rem 0; background: rgba(255,255,255,0.05); border-radius: 10px;">
                        <strong>Full Stack Developer</strong><br>
                        <small>Berlin/Remote • Full-time • €70-100k</small>
                    </li>
                </ul>
                <p>Send your resume to <a href="mailto:careers@kookooha.com" style="color: #6366f1;">careers@kookooha.com</a></p>
            </div>
        `,
        blog: `
            <h2>Latest from Our Blog</h2>
            <div style="margin: 2rem 0;">
                <div style="padding: 1.5rem; margin: 1rem 0; background: rgba(255,255,255,0.05); border-radius: 15px;">
                    <h3>The Science Behind Workplace Burnout</h3>
                    <p style="color: #94a3b8; margin: 0.5rem 0;">February 15, 2024</p>
                    <p>Understanding the neurological and psychological factors that contribute to employee burnout...</p>
                </div>
                <div style="padding: 1.5rem; margin: 1rem 0; background: rgba(255,255,255,0.05); border-radius: 15px;">
                    <h3>AI in Mental Health: Opportunities and Challenges</h3>
                    <p style="color: #94a3b8; margin: 0.5rem 0;">February 8, 2024</p>
                    <p>Exploring how artificial intelligence is revolutionizing workplace mental health monitoring...</p>
                </div>
            </div>
            <p>Visit our full blog at <a href="#" style="color: #6366f1;">blog.kookooha.com</a></p>
        `,
        support: `
            <h2>Support Center</h2>
            <div style="margin: 2rem 0;">
                <h3>How can we help you?</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
                    <div style="padding: 1.5rem; background: rgba(99,102,241,0.1); border-radius: 15px; text-align: center;">
                        <i class="fas fa-book" style="font-size: 2rem; color: #6366f1; margin-bottom: 1rem;"></i>
                        <h4>Documentation</h4>
                        <p>Comprehensive guides and API documentation</p>
                    </div>
                    <div style="padding: 1.5rem; background: rgba(99,102,241,0.1); border-radius: 15px; text-align: center;">
                        <i class="fas fa-life-ring" style="font-size: 2rem; color: #6366f1; margin-bottom: 1rem;"></i>
                        <h4>Live Support</h4>
                        <p>Chat with our support team 24/7</p>
                    </div>
                </div>
                <p>Contact us at <a href="mailto:support@kookooha.com" style="color: #6366f1;">support@kookooha.com</a> or call +49 30 1234 5678</p>
            </div>
        `,
        privacy: `
            <h2>Privacy Policy</h2>
            <div style="margin: 2rem 0; max-height: 400px; overflow-y: auto;">
                <h3>Data Collection</h3>
                <p>We collect only the necessary data to provide our services effectively while maintaining strict privacy standards.</p>
                
                <h3>Data Usage</h3>
                <p>Your data is used solely for improving workplace mental health insights and is never shared with third parties without explicit consent.</p>
                
                <h3>Data Security</h3>
                <p>We employ enterprise-grade encryption and security measures to protect your information.</p>
                
                <h3>Your Rights</h3>
                <p>You have the right to access, modify, or delete your personal data at any time.</p>
                
                <p style="margin-top: 2rem;"><small>Last updated: February 2024</small></p>
            </div>
        `,
        terms: `
            <h2>Terms of Service</h2>
            <div style="margin: 2rem 0; max-height: 400px; overflow-y: auto;">
                <h3>Service Agreement</h3>
                <p>By using Kookooha's services, you agree to these terms and conditions.</p>
                
                <h3>Service Scope</h3>
                <p>Our services include workplace mental health assessment, monitoring, and transformation programs.</p>
                
                <h3>User Responsibilities</h3>
                <p>Users must provide accurate information and comply with our usage guidelines.</p>
                
                <h3>Limitation of Liability</h3>
                <p>Kookooha provides services to the best of our ability but cannot guarantee specific outcomes.</p>
                
                <p style="margin-top: 2rem;"><small>Last updated: February 2024</small></p>
            </div>
        `
    };
    
    return contents[type] || '<p>Content not found.</p>';
}

// Enhanced Calculator with Currency Support
function initializeCalculator() {
    const peopleRange = document.getElementById('peopleCount');
    const criteriaRange = document.getElementById('criteriaCount');
    
    if (peopleRange && criteriaRange) {
        peopleRange.addEventListener('input', updateCalculator);
        criteriaRange.addEventListener('input', updateCalculator);
        updateCalculator();
    }

    function updateCalculator() {
        const people = parseInt(peopleRange.value);
        const criteria = parseInt(criteriaRange.value);
        
        // Update displays
        document.getElementById('peopleDisplay').textContent = people;
        document.getElementById('criteriaDisplay').textContent = criteria;
        
        // Calculate prices
        const basePeople = 4;
        const baseCriteria = 2;
        const basePrice = 750;
        const pricePerPerson = 75;
        const pricePerCriteria = 150;
        
        let additionalPeople = Math.max(0, people - basePeople);
        let additionalCriteriaCount = Math.max(0, criteria - baseCriteria);
        
        let additionalPeopleCost = additionalPeople * pricePerPerson;
        let additionalCriteriaCost = additionalCriteriaCount * pricePerCriteria;
        
        let total = basePrice + additionalPeopleCost + additionalCriteriaCost;
        
        // Update price displays
        document.getElementById('additionalPeoplePrice').textContent = `€${additionalPeopleCost}`;
        document.getElementById('additionalCriteriaPrice').textContent = `€${additionalCriteriaCost}`;
        document.getElementById('totalPrice').textContent = total.toLocaleString();
        
        // Show/hide additional rows
        document.getElementById('additionalPeopleRow').style.display = additionalPeople > 0 ? 'flex' : 'none';
        document.getElementById('additionalCriteriaRow').style.display = additionalCriteriaCount > 0 ? 'flex' : 'none';
    }
}

// Enhanced Forms with Validation
function initializeForms() {
    // Contact form
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', submitContactForm);
    }
    
    // Waitlist forms
    document.querySelectorAll('.waitlist-form').forEach(form => {
        form.addEventListener('submit', joinWaitlist);
    });
    
    // Newsletter forms
    document.querySelectorAll('.newsletter-form').forEach(form => {
        form.addEventListener('submit', subscribeNewsletter);
    });
}

function submitContactForm(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    // Basic validation
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#ef4444';
            isValid = false;
        } else {
            field.style.borderColor = '';
        }
    });
    
    if (!isValid) {
        showNotification(translations[currentLanguage]['notification.email.invalid'] || 'Please fill in all required fields.', 'error');
        return;
    }
    
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    submitButton.disabled = true;
    
    // Simulate form submission
    setTimeout(() => {
        showNotification(translations[currentLanguage]['notification.contact.success'], 'success');
        form.reset();
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }, 2000);
}

function joinWaitlist(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.querySelector('input[type="email"]').value;
    
    if (!validateEmail(email)) {
        showNotification(translations[currentLanguage]['notification.email.invalid'], 'error');
        return;
    }
    
    const button = form.querySelector('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    setTimeout(() => {
        showNotification(translations[currentLanguage]['notification.waitlist.success'], 'success');
        form.reset();
        button.innerHTML = originalText;
        button.disabled = false;
    }, 1500);
}

function subscribeNewsletter(event) {
    event.preventDefault();
    
    const form = event.target;
    const email = form.querySelector('input[type="email"]').value;
    
    if (!validateEmail(email)) {
        showNotification(translations[currentLanguage]['notification.email.invalid'], 'error');
        return;
    }
    
    const button = form.querySelector('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    setTimeout(() => {
        showNotification(translations[currentLanguage]['notification.newsletter.success'], 'success');
        form.reset();
        button.innerHTML = originalText;
        button.disabled = false;
    }, 1000);
}

// Keep all other functions from the original code (hidePreloader, initializeNavigation, etc.)
// but optimize them for performance and better user experience

function hidePreloader() {
    setTimeout(() => {
        const preloader = document.getElementById('preloader');
        if (preloader) {
            preloader.classList.add('hide');
            setTimeout(() => preloader.style.display = 'none', 500);
        }
    }, 1200);
}

function initializeNavigation() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    const navLinks = document.querySelectorAll('.nav-link');

    if (navToggle) {
        navToggle.addEventListener('click', toggleMobileMenu);
    }

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (isNavMenuOpen) toggleMobileMenu();
        });
    });

    updateActiveNavLink();
}

function toggleMobileMenu() {
    const navMenu = document.getElementById('navMenu');
    const navToggle = document.getElementById('navToggle');
    
    if (navMenu && navToggle) {
        isNavMenuOpen = !isNavMenuOpen;
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
        document.body.style.overflow = isNavMenuOpen ? 'hidden' : '';
    }
}

function updateActiveNavLink() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    
    window.addEventListener('scroll', () => {
        let current = '';
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop - 100;
            const sectionHeight = section.clientHeight;
            
            if (window.pageYOffset >= sectionTop && 
                window.pageYOffset < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (href === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
}

function handleScroll() {
    const navbar = document.getElementById('navbar');
    const scrollIndicator = document.querySelector('.scroll-indicator');
    
    if (navbar) {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    }
    
    if (scrollIndicator) {
        scrollIndicator.style.opacity = window.scrollY > 100 ? '0' : '0.5';
    }
    
    animateOnScroll();
}

function initializeScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.animate-on-scroll').forEach(element => {
        observer.observe(element);
    });
}

function animateOnScroll() {
    document.querySelectorAll('.animate-on-scroll:not(.visible)').forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        if (elementTop < window.innerHeight - 150) {
            element.classList.add('visible');
        }
    });
}

function initializeHeroSection() {
    animateStats();
    startFloatingShapesAnimation();
}

function animateStats() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-count'));
                animateCounter(entry.target, target);
                observer.unobserve(entry.target);
            }
        });
    });

    document.querySelectorAll('.stat-number').forEach(stat => {
        observer.observe(stat);
    });
}

function animateCounter(element, target) {
    let current = 0;
    const increment = target / 50;
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 40);
}

function startFloatingShapesAnimation() {
    document.querySelectorAll('.shape').forEach((shape, index) => {
        shape.style.animationDelay = `${index * 2}s`;
    });
}

function initializeCharts() {
    if (typeof Chart === 'undefined') return;
    initializeHeroChart();
    initializeAIVisualization();
}

function initializeHeroChart() {
    const canvas = document.getElementById('heroChart');
    if (!canvas) return;

    heroChart = new Chart(canvas.getContext('2d'), {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [{
                data: [65, 72, 78, 85, 87, 90],
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { display: false } },
            elements: { point: { radius: 0 } }
        }
    });
}

function initializeAIVisualization() {
    const canvas = document.getElementById('aiVisualization');
    if (!canvas) return;

    aiChart = new Chart(canvas.getContext('2d'), {
        type: 'scatter',
        data: {
            datasets: [{
                data: Array.from({length: 20}, () => ({
                    x: Math.random() * 100,
                    y: Math.random() * 100
                })),
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: '#6366f1',
                pointRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { display: false }, y: { display: false } },
            animation: { duration: 2000, easing: 'easeInOutQuart' }
        }
    });
}

function initializeParticleSystem() {
    const container = document.getElementById('particles');
    if (!container) return;

    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        
        const size = Math.random() * 3 + 2;
        particle.style.width = particle.style.height = size + 'px';
        
        container.appendChild(particle);
    }
}

function initializeClientsCarousel() {
    const track = document.getElementById('clientsCarousel');
    if (!track) return;

    const children = Array.from(track.children);
    children.forEach(child => {
        track.appendChild(child.cloneNode(true));
    });
}

function closeModal() {
    const modal = document.getElementById('modal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

function initializeModals() {
    const modal = document.getElementById('modal');
    if (!modal) return;
    
    modal.addEventListener('click', (e) => {
        if (e.target === modal || e.target.classList.contains('modal-overlay')) {
            closeModal();
        }
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            closeModal();
        }
    });
}

function initializeTooltips() {
    document.querySelectorAll('.info-tooltip').forEach(trigger => {
        trigger.addEventListener('mouseenter', showTooltipHandler);
        trigger.addEventListener('mouseleave', hideTooltipHandler);
    });
}

function showTooltipHandler(event) {
    const tooltip = document.getElementById('tooltip');
    const tooltipContent = document.getElementById('tooltipContent');
    if (!tooltip || !tooltipContent) return;
    
    const contents = {
        people: 'Select the number of employees in your organization who will participate in the assessment.',
        criteria: 'Choose how many specific research criteria you want to focus on (e.g., stress levels, team dynamics, communication patterns).'
    };
    
    tooltipContent.textContent = contents.people; // Default content
    
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 + 'px';
    tooltip.style.top = rect.bottom + 10 + 'px';
    tooltip.classList.add('show');
}

function hideTooltipHandler() {
    const tooltip = document.getElementById('tooltip');
    if (tooltip) tooltip.classList.remove('show');
}

function initializeStripe() {
    if (typeof Stripe !== 'undefined') {
        stripe = Stripe('pk_test_your_stripe_key_here');
    }
}

function proceedToCheckout() {
    const button = document.querySelector('[onclick="proceedToCheckout()"]');
    if (!button) return;
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    button.disabled = true;
    
    setTimeout(() => {
        showNotification(translations[currentLanguage]['notification.checkout.processing'], 'info');
        button.innerHTML = originalText;
        button.disabled = false;
    }, 2000);
}

function playDemo() {
    showNotification('Demo video would play here. Integration with video platform needed.', 'info');
}

function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');
            const target = document.querySelector(href);
            
            if (target && href !== '#') {
                e.preventDefault();
                window.scrollTo({
                    top: target.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function handleResize() {
    if (window.innerWidth > 768 && isNavMenuOpen) {
        toggleMobileMenu();
    }
    
    if (heroChart) heroChart.resize();
    if (aiChart) aiChart.resize();
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        background: ${getNotificationColor(type)}; color: white;
        padding: 1rem 1.5rem; border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        display: flex; align-items: center; gap: 1rem; max-width: 400px;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOutRight 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = { success: 'check-circle', error: 'exclamation-triangle', warning: 'exclamation-circle', info: 'info-circle' };
    return icons[type] || 'info-circle';
}

function getNotificationColor(type) {
    const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#6366f1' };
    return colors[type] || '#6366f1';
}

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// Add notification styles
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    .notification-content { display: flex; align-items: center; gap: 0.5rem; flex: 1; }
    .notification-close { background: none; border: none; color: white; cursor: pointer; opacity: 0.7; transition: opacity 0.2s; }
    .notification-close:hover { opacity: 1; }
`;
document.head.appendChild(notificationStyles);

// Global function exports
window.showModal = showModal;
window.closeModal = closeModal;
window.proceedToCheckout = proceedToCheckout;
window.playDemo = playDemo;
window.submitContactForm = submitContactForm;
window.joinWaitlist = joinWaitlist;
window.subscribeNewsletter = subscribeNewsletter;