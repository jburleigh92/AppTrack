import logging
from typing import List, Dict, Any, Set
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData
from app.services.scraping.greenhouse_api import fetch_all_greenhouse_jobs

router = APIRouter()
logger = logging.getLogger(__name__)

# Target companies to fetch jobs from (Greenhouse job boards)
# These are popular tech companies with public Greenhouse boards
TARGET_COMPANIES = [
    "airbnb",
    "stripe",
    "shopify",
    "coinbase",
    "dropbox",
    "instacart",
    "robinhood",
    "doordash",
    "gitlab",
    "notion",
]

# Comprehensive technical skills dictionary for job extraction
# Organized by category for maintainability
TECHNICAL_SKILLS = {
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby",
    "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell", "Bash",

    # Web Frameworks & Libraries
    "React", "Angular", "Vue", "Svelte", "Next.js", "Nuxt", "Django", "Flask",
    "FastAPI", "Express", "Node.js", "Spring", "Spring Boot", "Rails", "Laravel",
    "ASP.NET", "jQuery", "Bootstrap", "Tailwind", "Material-UI", "Redux", "GraphQL",

    # Databases & Storage
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "DynamoDB", "Oracle", "SQL Server", "MariaDB", "Neo4j", "CouchDB", "InfluxDB",
    "Snowflake", "BigQuery", "Redshift",

    # Cloud & Infrastructure
    "AWS", "Azure", "GCP", "Google Cloud", "Heroku", "DigitalOcean", "Vercel",
    "Netlify", "Cloudflare", "Lambda", "EC2", "S3", "CloudFormation", "ARM",

    # DevOps & Tools
    "Docker", "Kubernetes", "K8s", "Terraform", "Ansible", "Jenkins", "CircleCI",
    "GitHub Actions", "GitLab CI", "Travis CI", "Prometheus", "Grafana", "Datadog",
    "New Relic", "Splunk", "ELK", "Kafka", "RabbitMQ", "Nginx", "Apache",

    # Data & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
    "Pandas", "NumPy", "Jupyter", "Spark", "Hadoop", "Airflow", "dbt", "Tableau",
    "Power BI", "Looker", "ML", "AI", "NLP", "Computer Vision", "LLM",

    # Mobile
    "iOS", "Android", "React Native", "Flutter", "SwiftUI", "UIKit", "Jetpack Compose",

    # Testing & Quality
    "Jest", "Pytest", "JUnit", "Selenium", "Cypress", "TestNG", "Mocha", "Chai",
    "TDD", "CI/CD", "QA",

    # Methodologies & Concepts
    "Agile", "Scrum", "Kanban", "Microservices", "REST", "API", "gRPC", "WebSockets",
    "OAuth", "SAML", "JWT", "Git", "GitHub", "GitLab", "Bitbucket", "JIRA",
    "Confluence", "Slack", "Linux", "Unix", "Windows", "macOS",

    # Security
    "Security", "Cybersecurity", "Penetration Testing", "OWASP", "Encryption", "SSL",
    "TLS", "VPN", "Firewall", "IAM",

    # Emerging Tech
    "Blockchain", "Ethereum", "Solidity", "Web3", "NFT", "Cryptocurrency", "Bitcoin",
    "AR", "VR", "IoT", "Edge Computing", "Serverless",

    # Soft Skills (Technical Adjacent)
    "Leadership", "Mentoring", "Architecture", "System Design", "Problem Solving",
    "Communication", "Collaboration", "Code Review"
}


def _extract_skills_from_job(text: str) -> Set[str]:
    """
    Extract technical skills from job description.

    Uses comprehensive skill dictionary to find ALL technical skills mentioned,
    not limited to candidate's resume skills.

    Returns:
        Set of skills found in job description (preserves original case from dictionary)
    """
    if not text:
        return set()

    text_lower = text.lower()
    found_skills = set()

    for skill in TECHNICAL_SKILLS:
        # Use word boundary matching to avoid false positives
        # e.g., "Go" should match "Go programming" but not "Google"
        skill_lower = skill.lower()

        # Simple substring match (can be improved with regex word boundaries)
        if skill_lower in text_lower:
            found_skills.add(skill)

    return found_skills


def _infer_skills_from_title(title: str) -> Set[str]:
    """
    Infer likely technical skills from job title.

    Aggressively extracts skills to maximize matching when job content unavailable.
    Uses multi-pass approach: direct skill mentions, role keywords, seniority hints.
    """
    if not title:
        return set()

    title_lower = title.lower()
    inferred = set()

    # PASS 1: Direct skill mentions in title (e.g., "Python Engineer", "React Developer")
    for skill in TECHNICAL_SKILLS:
        if skill.lower() in title_lower:
            inferred.add(skill)

    # PASS 2: Role-based inference with expanded, comprehensive skill sets
    role_skills = {
        # Frontend roles
        "frontend": {"JavaScript", "TypeScript", "React", "Angular", "Vue", "HTML", "CSS",
                     "Redux", "Webpack", "Git", "API", "Web"},
        "front end": {"JavaScript", "TypeScript", "React", "Angular", "Vue", "HTML", "CSS",
                      "Redux", "Webpack", "Git", "API", "Web"},
        "ui": {"JavaScript", "TypeScript", "React", "HTML", "CSS", "Design"},
        "web developer": {"JavaScript", "HTML", "CSS", "React", "Node.js", "API", "Git"},

        # Backend roles
        "backend": {"API", "Database", "SQL", "Python", "Java", "Go", "Node.js",
                    "Microservices", "REST", "PostgreSQL", "Redis", "Git"},
        "back end": {"API", "Database", "SQL", "Python", "Java", "Go", "Node.js",
                     "Microservices", "REST", "PostgreSQL", "Redis", "Git"},
        "api": {"API", "REST", "GraphQL", "Microservices", "Database", "Python", "Node.js"},

        # Fullstack roles
        "fullstack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                      "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},
        "full stack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                       "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},
        "full-stack": {"JavaScript", "TypeScript", "Python", "React", "Node.js", "API",
                       "Database", "SQL", "PostgreSQL", "Git", "HTML", "CSS", "REST"},

        # Generic engineering (broadest match - catches "Senior Engineer", "Staff Engineer")
        "software engineer": {"Python", "JavaScript", "Java", "Git", "API", "Database", "SQL",
                              "Problem Solving", "System Design", "Agile"},
        "engineer": {"Git", "Problem Solving", "System Design", "API", "Database"},
        "developer": {"Git", "API", "Database", "Problem Solving"},
        "programmer": {"Git", "Problem Solving"},

        # DevOps/Infrastructure
        "devops": {"Docker", "Kubernetes", "CI/CD", "AWS", "Linux", "Terraform", "Git",
                   "Jenkins", "Python", "Bash"},
        "sre": {"Kubernetes", "Docker", "Monitoring", "Linux", "Python", "AWS", "Terraform"},
        "infrastructure": {"Docker", "Kubernetes", "Terraform", "AWS", "Linux", "Networking"},
        "platform": {"Kubernetes", "Docker", "CI/CD", "AWS", "Infrastructure", "Python"},

        # Data roles
        "data engineer": {"Python", "SQL", "Spark", "Airflow", "Kafka", "Database", "ETL"},
        "data scientist": {"Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Statistics"},
        "data": {"Python", "SQL", "Database", "Analytics"},
        "analytics": {"SQL", "Python", "Tableau", "Analytics"},

        # ML/AI roles
        "ml": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "Scikit-learn"},
        "machine learning": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "Deep Learning"},
        "ai": {"Python", "Machine Learning", "TensorFlow", "PyTorch", "AI"},

        # Mobile
        "mobile": {"iOS", "Android", "React Native", "Flutter", "Mobile"},
        "ios": {"Swift", "iOS", "SwiftUI", "UIKit", "Xcode"},
        "android": {"Kotlin", "Java", "Android", "Jetpack Compose"},

        # Security
        "security": {"Security", "Cybersecurity", "Encryption", "Networking", "Linux"},

        # Cloud
        "cloud": {"AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform"},
    }

    for keyword, skills in role_skills.items():
        if keyword in title_lower:
            inferred.update(skills)

    # PASS 3: If still no skills, use generic tech baseline
    if not inferred:
        inferred = {"Git", "Problem Solving", "Communication", "Agile"}

    return inferred


def _extract_skills_from_text(text: str, known_skills: List[str]) -> List[str]:
    """
    Extract skills from job description text by matching against known skills.
    Case-insensitive matching.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = []

    for skill in known_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


@router.get("/discover")
def discover_jobs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Discover jobs from Greenhouse job boards based on active resume skills.

    Fetches available jobs from configured companies' Greenhouse boards
    and matches them against the user's resume.
    """
    # Get active resume
    resume = db.query(Resume).filter(Resume.is_active == True).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No active resume found. Please upload a resume first."
        )

    # Get resume data
    resume_data = db.query(ResumeData).filter(
        ResumeData.resume_id == resume.id
    ).first()

    if not resume_data or not resume_data.extraction_complete:
        raise HTTPException(
            status_code=400,
            detail="Resume parsing not complete"
        )

    # Extract skills from resume
    user_skills = resume_data.skills if resume_data.skills else []
    user_skills_set = set(skill.lower() for skill in user_skills) if user_skills else set()

    # Fetch jobs from all target companies
    all_jobs = []
    for company_slug in TARGET_COMPANIES:
        company_jobs = fetch_all_greenhouse_jobs(company_slug)
        all_jobs.extend(company_jobs)

    # 1️⃣ Log: Jobs entering matcher
    logger.info(
        "matcher.start",
        extra={
            "jobs_received": len(all_jobs),
            "user_skills_count": len(user_skills),
            "resume_id": str(resume.id)
        }
    )

    if not all_jobs:
        logger.info(
            "Job discovery returned no jobs from Greenhouse",
            extra={
                "resume_id": str(resume.id),
                "user_skills_count": len(user_skills),
                "companies_checked": len(TARGET_COMPANIES)
            }
        )
        return []

    # Match jobs to user skills - track elimination reasons
    matched_jobs = []
    match_scores = []

    # Elimination counters
    eliminated_no_content = 0
    eliminated_no_resume_skills = 0
    eliminated_no_job_skills = 0
    eliminated_no_skill_match = 0

    for job in all_jobs:
        # Extract job details from Greenhouse API response
        job_id = job.get("id")
        job_title = job.get("title", "")
        company_name = job.get("company_name", "Unknown Company")
        location = job.get("location", {}).get("name", "Location not specified")
        absolute_url = job.get("absolute_url", "")

        # Get job content for skill matching (may be empty from list endpoint)
        job_content = job.get("content", "")

        # Track elimination: no title or content to analyze
        if not job_title and not job_content:
            eliminated_no_content += 1
            continue

        # Track elimination: no resume skills
        if not user_skills:
            eliminated_no_resume_skills += 1
            continue

        # Extract ALL technical skills from job description (if available)
        job_skills_extracted = _extract_skills_from_job(job_content) if job_content else set()

        # CRITICAL: Greenhouse list endpoint doesn't include 'content' field
        # Fall back to title-based skill inference for all jobs
        title_skills = _infer_skills_from_title(job_title)
        job_skills_extracted.update(title_skills)

        # Track elimination: no job skills found (even with title fallback)
        if not job_skills_extracted:
            eliminated_no_job_skills += 1
            continue

        # Calculate skill overlap with user resume
        job_skills_lower = set(skill.lower() for skill in job_skills_extracted)
        matched_skills = job_skills_lower.intersection(user_skills_set)

        # Track elimination: no skill match
        if not matched_skills:
            eliminated_no_skill_match += 1
            continue

        # Job passed all filters - calculate score
        match_count = len(matched_skills)
        # Score as percentage of job's required skills that user has
        match_percentage = int((match_count / len(job_skills_lower)) * 100)
        match_reason = ", ".join(sorted(skill.title() for skill in matched_skills))

        # Track score for distribution
        match_scores.append(match_percentage)

        # Only include jobs with at least one skill match
        matched_jobs.append({
            "id": str(job_id),
            "title": job_title,
            "company": company_name,
            "url": absolute_url,
            "location": location,
            "match_reason": match_reason,
            "match_percentage": match_percentage,
            "description": job_content[:200] + "..." if len(job_content) > 200 else job_content,
            "source": "greenhouse"
        })

    # 2️⃣ Log: Score distribution
    if match_scores:
        logger.info(
            "matcher.scores",
            extra={
                "min": min(match_scores),
                "max": max(match_scores),
                "avg": sum(match_scores) / len(match_scores)
            }
        )
    else:
        logger.info("matcher.scores", extra={"status": "unavailable"})

    # 3️⃣ Log: Elimination reasons (counts)
    logger.info(
        "matcher.filtered",
        extra={
            "no_content": eliminated_no_content,
            "no_resume_skills": eliminated_no_resume_skills,
            "no_job_skills": eliminated_no_job_skills,
            "no_skill_match": eliminated_no_skill_match
        }
    )

    # Sort by match percentage (highest first)
    matched_jobs.sort(key=lambda x: x["match_percentage"], reverse=True)

    # 4️⃣ Log: Final output count
    logger.info(
        "matcher.result",
        extra={
            "count": len(matched_jobs),
            "resume_id": str(resume.id)
        }
    )

    return matched_jobs
