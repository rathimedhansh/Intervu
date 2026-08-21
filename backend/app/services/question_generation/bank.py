# Local, static question bank used by the mock provider (and as the source
# of truth for the role dropdown on the frontend). No network calls, no AI —
# every bucket below is hand-written.
#
# InterviewCreate.role (app/schemas/interview.py) is a plain validated
# string, not a Literal restricted to this tuple — the frontend also offers
# an "Other / Custom Role" option that submits arbitrary text. A role not
# found here (curated or custom) still works end-to-end: QUESTION_BANK.get()
# falls back to the "General" pool below, and the AI-backed providers
# (anthropic_provider.py, services/interview_flow) and answer evaluation /
# feedback already treat role as free text.

ROLES = (
    "Software Engineer",
    "Frontend Engineer",
    "Backend Engineer",
    "Full Stack Engineer",
    "Mobile Developer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Data Engineer",
    "ML Engineer",
    "AI Engineer",
    "Cybersecurity Engineer",
    "QA/Automation Engineer",
    "Data Scientist",
    "Data Analyst",
    "AI Researcher",
    "Product Manager",
    "Business Analyst",
    "Project Manager",
    "UX/UI Designer",
)

# role -> difficulty -> questions. "General" is a role-agnostic fallback
# bucket used to pad out a role's pool when more questions are requested
# than that role/difficulty combination has on its own.
QUESTION_BANK: dict[str, dict[str, list[str]]] = {
    "Software Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to software engineering.",
            "What programming languages are you most comfortable with, and why?",
            "Describe a small project you built and what it does.",
            "How do you approach learning a new framework or library?",
        ],
        "medium": [
            "Describe a challenging bug you fixed. How did you track it down?",
            "How do you decide between writing a quick fix and a proper refactor?",
            "Tell me about a time you had to review a teammate's code that had issues. How did you handle it?",
            "Walk me through how you'd design a URL shortener at a high level.",
        ],
        "hard": [
            "Describe a system you designed that had to scale significantly. What were the bottlenecks?",
            "Tell me about a production incident you were involved in. What was the root cause and how did you prevent recurrence?",
            "How would you design a rate limiter for a public API?",
            "Describe a time you disagreed with a technical decision made by a senior engineer. What did you do?",
        ],
    },
    "Frontend Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to frontend engineering.",
            "What's the difference between state and props in a component-based framework?",
            "How do you make sure a web page is accessible?",
            "Describe a UI you built that you're proud of.",
        ],
        "medium": [
            "How do you approach debugging a layout issue that only appears in one browser?",
            "Tell me about a time you had to optimize a slow-rendering page. What did you do?",
            "How do you decide when to introduce global state versus keeping state local to a component?",
            "Walk me through how you'd structure a component library for a growing product.",
        ],
        "hard": [
            "Describe a time you led a significant frontend architecture migration. What was hard about it?",
            "How would you design a client-side caching strategy for a data-heavy dashboard?",
            "Tell me about a performance regression you diagnosed in production. How did you find it?",
            "How do you balance developer experience against bundle size and runtime performance?",
        ],
    },
    "Backend Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to backend engineering.",
            "What's the difference between SQL and NoSQL databases, and when would you use each?",
            "How do you approach writing an API endpoint from scratch?",
            "Describe a backend service you built and what it does.",
        ],
        "medium": [
            "Describe a time you had to optimize a slow database query. What was your process?",
            "How do you approach designing a REST API for a new resource?",
            "Tell me about a time a service you owned went down. What happened?",
            "How do you decide when to introduce caching, and where?",
        ],
        "hard": [
            "How would you design a system that processes millions of events per day reliably?",
            "Describe a time you had to make a tradeoff between consistency and availability.",
            "Tell me about a time you had to migrate a production database with zero downtime.",
            "How would you design an idempotent payment processing API?",
        ],
    },
    "Full Stack Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to full stack development.",
            "How do you decide which parts of a feature belong on the frontend versus the backend?",
            "Describe a full stack project you built end-to-end.",
            "What's your process for keeping the frontend and backend in sync as an API evolves?",
        ],
        "medium": [
            "Describe a time you had to debug an issue that spanned both the frontend and backend. How did you track it down?",
            "How do you approach designing the contract (API shape) between frontend and backend before either side is built?",
            "Tell me about a time you had to make a tradeoff between doing something client-side versus server-side.",
            "Walk me through how you'd add real-time updates to an existing full stack application.",
        ],
        "hard": [
            "Describe a full stack system you owned end-to-end that had to scale. What broke first?",
            "How would you design authentication and session handling across a full stack app with a separate frontend and backend?",
            "Tell me about a time a change on one side of the stack caused a production issue on the other side.",
            "How do you decide when a full stack team should split into dedicated frontend/backend roles versus staying full stack?",
        ],
    },
    "Mobile Developer": {
        "easy": [
            "Tell me about yourself and what draws you to mobile development.",
            "What's the difference between native and cross-platform mobile development, and when would you choose each?",
            "Describe a mobile app you built and what it does.",
            "How do you approach testing a mobile app across different devices and screen sizes?",
        ],
        "medium": [
            "Describe a time you had to optimize a mobile app's performance or battery usage. What did you do?",
            "How do you handle offline support and syncing data once connectivity returns?",
            "Tell me about a time you had to work around platform-specific (iOS vs Android) differences.",
            "How do you approach managing app state across screens in a mobile app?",
        ],
        "hard": [
            "Describe a time you had to diagnose a crash or ANR (App Not Responding) issue that only showed up in production.",
            "How would you design a mobile app's architecture to support both offline-first usage and real-time sync?",
            "Tell me about a time you had to plan a mobile app migration with minimal disruption to users.",
            "How do you approach managing app releases and rollouts across app stores with strict review processes?",
        ],
    },
    "DevOps Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to DevOps.",
            "What's the difference between continuous integration and continuous deployment?",
            "Describe a CI/CD pipeline you've worked with and what it does.",
            "How do you approach automating a repetitive manual deployment task?",
        ],
        "medium": [
            "Describe a time you improved a slow or flaky CI/CD pipeline. What did you do?",
            "How do you approach rolling out a change safely to production (e.g., canary, blue-green)?",
            "Tell me about a time an infrastructure change caused an outage. What happened?",
            "How do you decide what should be automated versus done manually in a deployment process?",
        ],
        "hard": [
            "How would you design a zero-downtime deployment strategy for a stateful service?",
            "Tell me about a time you had to respond to a major production incident. What was your process?",
            "How would you design infrastructure-as-code for a multi-environment (dev/staging/prod) setup?",
            "Describe a time you had to balance developer velocity against operational stability.",
        ],
    },
    "Cloud Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to cloud engineering.",
            "What's the difference between IaaS, PaaS, and SaaS?",
            "Describe a cloud-based system or service you've worked with.",
            "How do you approach choosing between different cloud storage options for a given use case?",
        ],
        "medium": [
            "Describe a time you had to optimize cloud infrastructure costs. What did you do?",
            "How do you approach designing for high availability across multiple regions or availability zones?",
            "Tell me about a time a cloud service outage affected your system. How did you handle it?",
            "How do you decide between managed services and self-hosting a piece of infrastructure?",
        ],
        "hard": [
            "How would you design a multi-region, highly available cloud architecture for a critical service?",
            "Tell me about a time you had to migrate a significant workload from one cloud provider or architecture to another.",
            "How would you approach securing a cloud environment against misconfigurations and unauthorized access?",
            "Describe a time you had to make a tradeoff between cost, performance, and reliability in a cloud architecture.",
        ],
    },
    "Data Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to data engineering.",
            "What's the difference between a data warehouse and a data lake?",
            "Describe a data pipeline you've built and what it does.",
            "How do you approach validating the quality of data flowing through a pipeline?",
        ],
        "medium": [
            "Describe a time you had to optimize a slow or expensive data pipeline. What was your process?",
            "How do you approach designing a pipeline that needs to handle both batch and streaming data?",
            "Tell me about a time a data pipeline failed silently. How did you catch it, and what did you change?",
            "How do you decide on a schema design for a dataset that multiple downstream teams depend on?",
        ],
        "hard": [
            "How would you design a data pipeline that needs to process billions of events per day reliably?",
            "Tell me about a time you had to backfill or reprocess a large dataset with minimal disruption to downstream consumers.",
            "How would you design a system to guarantee data consistency across multiple pipelines writing to the same destination?",
            "Describe a time you had to make a tradeoff between data freshness and pipeline cost or complexity.",
        ],
    },
    "ML Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to machine learning engineering.",
            "What's the difference between training and inference, and why does that distinction matter for system design?",
            "Describe a machine learning model you've helped deploy or productionize.",
            "How do you approach versioning models and datasets?",
        ],
        "medium": [
            "Describe a time you had to debug a model that performed well offline but poorly in production.",
            "How do you approach designing a feature pipeline that's consistent between training and serving?",
            "Tell me about a time you had to optimize a model's inference latency or cost.",
            "How do you decide when to retrain a model versus adjust the surrounding system?",
        ],
        "hard": [
            "How would you design a system to detect and respond to model drift in production?",
            "Tell me about a time you had to roll back a model deployment. What was your process?",
            "How would you design an ML platform that supports multiple teams training and deploying models independently?",
            "Describe a time you had to balance model accuracy against latency, cost, or interpretability requirements.",
        ],
    },
    "AI Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to AI engineering.",
            "What's the difference between a traditional ML model and a large language model, from an engineering perspective?",
            "Describe an AI-powered feature you've built or integrated into a product.",
            "How do you approach evaluating whether an AI feature is actually working well?",
        ],
        "medium": [
            "Describe a time you had to reduce hallucinations or improve the reliability of an AI system's output.",
            "How do you approach designing a system that combines a language model with retrieval or external tools?",
            "Tell me about a time you had to optimize the cost or latency of an AI-powered feature.",
            "How do you handle validating and constraining AI-generated output before it reaches a user?",
        ],
        "hard": [
            "How would you design a production system around a large language model that needs to stay reliable as the underlying model changes?",
            "Tell me about a time you had to debug an AI system whose behavior was hard to reproduce.",
            "How would you design guardrails and monitoring for an AI feature that takes actions on a user's behalf?",
            "Describe a time you had to make a tradeoff between AI capability and safety, cost, or predictability.",
        ],
    },
    "Cybersecurity Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to cybersecurity.",
            "What's the difference between authentication and authorization?",
            "Describe a security improvement you made to a system you worked on.",
            "How do you approach keeping up with new vulnerabilities and threats?",
        ],
        "medium": [
            "Describe a time you identified a security vulnerability in a system. How did you find it and what did you do?",
            "How do you approach threat modeling a new feature before it ships?",
            "Tell me about a time you had to balance security requirements against product or engineering velocity.",
            "How do you decide what should be logged and monitored for security purposes without over-collecting sensitive data?",
        ],
        "hard": [
            "How would you design an incident response process for a suspected data breach?",
            "Tell me about a time you responded to an active security incident. What was your process?",
            "How would you design a system's architecture to minimize blast radius if one component is compromised?",
            "Describe a time you had to convince a team to prioritize a security fix over other roadmap work.",
        ],
    },
    "QA/Automation Engineer": {
        "easy": [
            "Tell me about yourself and what draws you to QA and test automation.",
            "What's the difference between unit, integration, and end-to-end tests?",
            "Describe a test suite or automation framework you've worked with.",
            "How do you decide what to test manually versus automate?",
        ],
        "medium": [
            "Describe a time you had to stabilize a flaky test suite. What was your process?",
            "How do you approach testing a feature that touches multiple services or systems?",
            "Tell me about a time a bug slipped through testing into production. What did you change afterward?",
            "How do you balance test coverage against the time it takes to run the full suite?",
        ],
        "hard": [
            "How would you design a test automation strategy for a large, fast-moving codebase with multiple teams shipping daily?",
            "Tell me about a time you had to make the case for investing in test infrastructure over feature work.",
            "How would you approach testing a system with significant asynchronous or distributed behavior?",
            "Describe a time you had to balance thorough testing against a tight release deadline.",
        ],
    },
    "Data Scientist": {
        "easy": [
            "Tell me about yourself and what draws you to data science.",
            "How would you explain a p-value to a non-technical stakeholder?",
            "What's the difference between supervised and unsupervised learning?",
            "Describe a dataset you analyzed and what you found.",
        ],
        "medium": [
            "Describe a time your analysis led to a business decision. What was the impact?",
            "How do you approach detecting and handling outliers in a dataset?",
            "Tell me about a model you built that underperformed in production. What went wrong?",
            "How would you design an A/B test to measure the impact of a new feature?",
        ],
        "hard": [
            "Describe a time you had to convince skeptical stakeholders to trust a model's output.",
            "How would you detect and address data drift in a production ML system?",
            "Tell me about the most complex feature engineering problem you've tackled.",
            "How would you design an experimentation platform for a company running hundreds of A/B tests?",
        ],
    },
    "Data Analyst": {
        "easy": [
            "Tell me about yourself and what draws you to data analysis.",
            "How would you explain a p-value to a non-technical stakeholder?",
            "Describe a dataset you analyzed and what you found.",
            "What's your process for making sure a dataset is clean before analyzing it?",
        ],
        "medium": [
            "Describe a time your analysis led to a business decision. What was the impact?",
            "How do you approach detecting and handling outliers in a dataset?",
            "Tell me about a time your analysis was misinterpreted by stakeholders. What did you do?",
            "How would you design a dashboard to track a new product metric?",
        ],
        "hard": [
            "Describe a time you had to convince skeptical stakeholders to trust your analysis or recommendation.",
            "How would you design an experiment to measure the impact of a new feature when a true A/B test isn't possible?",
            "Tell me about the most complex analysis you've done end-to-end, from question to recommendation.",
            "How do you approach analyses where the data available doesn't fully answer the business question being asked?",
        ],
    },
    "AI Researcher": {
        "easy": [
            "Tell me about yourself and what draws you to AI research.",
            "How would you explain overfitting to someone without a machine learning background?",
            "Describe a research project or paper you've worked on or studied closely.",
            "How do you approach reading and evaluating a new research paper?",
        ],
        "medium": [
            "Describe a time an experiment you ran didn't produce the result you expected. What did you do?",
            "How do you approach designing an experiment to isolate the effect of one change in a model or system?",
            "Tell me about a time you had to decide between a promising but risky research direction versus a safer, incremental one.",
            "How do you approach reproducing results from a paper or another researcher's work?",
        ],
        "hard": [
            "Describe the most technically challenging research problem you've worked on. What made it hard?",
            "How would you design a research agenda to investigate an open problem in your area of AI?",
            "Tell me about a time you had to communicate a nuanced research finding to a non-research audience.",
            "How do you balance research novelty against practical applicability when choosing what to work on?",
        ],
    },
    "Product Manager": {
        "easy": [
            "Tell me about yourself and what draws you to product management.",
            "How do you prioritize a backlog with limited engineering resources?",
            "Describe a product you admire and why.",
            "How do you gather feedback from users?",
        ],
        "medium": [
            "Tell me about a feature you shipped that didn't perform as expected. What did you learn?",
            "How do you handle disagreement between engineering and design on scope?",
            "Walk me through how you'd validate a new product idea before building it.",
            "How do you decide what metrics define success for a new feature?",
        ],
        "hard": [
            "Describe a time you had to sunset a product or feature. How did you manage that?",
            "Tell me about the hardest tradeoff you've had to make between short-term revenue and long-term product health.",
            "How would you approach entering a new, unfamiliar market with an existing product?",
            "Describe a time your product strategy was wrong. How did you find out, and what did you do?",
        ],
    },
    "Business Analyst": {
        "easy": [
            "Tell me about yourself and what draws you to business analysis.",
            "How do you approach gathering requirements from stakeholders with different priorities?",
            "Describe a business process you analyzed and improved.",
            "How do you document requirements so both technical and non-technical stakeholders understand them?",
        ],
        "medium": [
            "Tell me about a time you had to translate a vague business problem into clear requirements.",
            "How do you approach prioritizing conflicting requirements from different stakeholders?",
            "Describe a time your analysis uncovered a problem nobody had noticed yet.",
            "How do you validate that a proposed solution will actually solve the underlying business problem?",
        ],
        "hard": [
            "Describe a time you had to manage a complex requirements-gathering process across multiple departments.",
            "How would you approach analyzing whether a major process or system change is worth the investment?",
            "Tell me about a time you had to push back on a stakeholder's requirements because they didn't align with the actual business need.",
            "How do you measure whether a process improvement you recommended actually delivered value?",
        ],
    },
    "Project Manager": {
        "easy": [
            "Tell me about yourself and what draws you to project management.",
            "How do you approach creating a project timeline with realistic estimates?",
            "Describe a project you managed from start to finish.",
            "How do you keep a project team aligned on priorities?",
        ],
        "medium": [
            "Tell me about a time a project you managed fell behind schedule. What did you do?",
            "How do you approach managing scope creep on a project?",
            "Describe a time you had to manage a dependency on another team that was at risk.",
            "How do you decide what to escalate versus handle yourself as a project manager?",
        ],
        "hard": [
            "Describe the most complex, cross-functional project you've managed. What made it hard to coordinate?",
            "How would you approach recovering a project that's significantly behind schedule and over budget?",
            "Tell me about a time you had to manage conflicting priorities between stakeholders at different levels of the organization.",
            "How do you decide when to kill a project versus keep investing in it?",
        ],
    },
    "UX/UI Designer": {
        "easy": [
            "Tell me about yourself and what draws you to UX/UI design.",
            "What's the difference between UX and UI design?",
            "Describe a design you're proud of and why.",
            "How do you approach gathering feedback on a design from users?",
        ],
        "medium": [
            "Describe a time user research changed the direction of a design you were working on.",
            "How do you approach designing for accessibility?",
            "Tell me about a time you disagreed with an engineer or product manager about a design decision. How did you resolve it?",
            "How do you balance visual polish against usability and development effort?",
        ],
        "hard": [
            "Describe a time you led a significant redesign of an existing product. What was hard about it?",
            "How would you design a design system to scale consistently across a growing product with multiple teams?",
            "Tell me about a time you had to make a design decision with incomplete or conflicting user research.",
            "How do you measure whether a design change actually improved the user experience?",
        ],
    },
    "General": {
        "easy": [
            "What are you looking for in your next role?",
            "Describe your ideal work environment.",
            "How do you stay organized when juggling multiple tasks?",
            "Tell me about a time you had to learn something quickly.",
            "What's a piece of feedback you received that changed how you work?",
            "How do you handle a task with unclear requirements?",
        ],
        "medium": [
            "Tell me about a time you disagreed with a teammate. How did you resolve it?",
            "Describe a project that didn't go as planned. What did you do?",
            "How do you prioritize when everything feels urgent?",
            "Tell me about a time you had to persuade someone to see things your way.",
            "Describe a time you made a mistake at work. How did you handle it?",
            "How do you approach giving difficult feedback to a peer?",
        ],
        "hard": [
            "Tell me about the most difficult decision you've had to make under pressure.",
            "Describe a time you had to lead through significant ambiguity.",
            "Tell me about a time you failed publicly. What did you take away from it?",
            "How do you handle a situation where your manager disagrees with your approach?",
            "Describe a time you had to deliver bad news to stakeholders.",
            "Where do you see yourself in the next few years, and why this role?",
        ],
    },
}
