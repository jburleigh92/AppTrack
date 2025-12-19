import logging
from typing import List, Dict, Any, Set, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData
from app.services.scraping.greenhouse_api import fetch_all_greenhouse_jobs, fetch_greenhouse_job
from app.core.config import settings

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

    # Soft skills to exclude from direct title matching (too generic, cause false positives)
    SOFT_SKILLS = {
        "Leadership", "Mentoring", "Problem Solving", "Communication",
        "Collaboration", "Code Review"
    }

    # PASS 1: Direct skill mentions in title with word boundaries
    # (e.g., "Python Engineer", "React Developer")
    # Excludes soft skills to prevent matching non-technical roles
    import re
    for skill in TECHNICAL_SKILLS:
        if skill in SOFT_SKILLS:
            continue  # Skip soft skills in title matching

        # Use word boundary to prevent false positives (e.g., "digital" matching "Git")
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, title_lower):
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

    # PASS 3: Return empty if no technical role detected
    # This filters out non-technical roles (Communications, HR, Sales, etc.)
    # Better to have no match than false positive matches
    return inferred


def _passes_role_domain_filter(job_title: str) -> bool:
    """
    Configuration-driven role domain filter.

    Checks if job title matches the active role domain requirements.
    This is NOT hard-coded - configured via settings.ACTIVE_ROLE_DOMAIN.

    Returns:
        True if job passes filter, False if should be excluded
    """
    active_domain = settings.ACTIVE_ROLE_DOMAIN
    domain_config = settings.ROLE_DOMAINS.get(active_domain, {})

    require_keywords = domain_config.get("require_any", [])
    exclude_keywords = domain_config.get("exclude_any", [])

    title_lower = job_title.lower()

    # If exclude keywords present, check exclusions first
    for exclude_word in exclude_keywords:
        if exclude_word.lower() in title_lower:
            return False

    # If require keywords specified, check requirements
    if require_keywords:
        for require_word in require_keywords:
            if require_word.lower() in title_lower:
                return True
        return False  # No required keyword found

    # Default: pass if no constraints
    return True


def _enrich_job_with_description(company_slug: str, job_id: str, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch full job description for a single job.

    Used for selective enrichment of top candidates.
    Caches in job dict to avoid redundant API calls.

    Returns:
        Updated job dict with 'content' field, or None if fetch fails
    """
    if job.get("content"):
        return job  # Already has content

    # Fetch full job details
    full_job = fetch_greenhouse_job(company_slug, str(job_id))

    if full_job and full_job.get("content"):
        job["content"] = full_job["content"]
        job["enriched"] = True
        return job

    return None


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
        # Store company_slug in job for enrichment later
        for job in company_jobs:
            job["_company_slug"] = company_slug
        all_jobs.extend(company_jobs)

    # 1️⃣ ROLE DOMAIN GATE: Configuration-driven title filtering
    # Reduces candidate set before matching
    filtered_jobs = []
    eliminated_role_domain = 0

    for job in all_jobs:
        job_title = job.get("title", "")
        if _passes_role_domain_filter(job_title):
            filtered_jobs.append(job)
        else:
            eliminated_role_domain += 1

    # Log: Jobs after role domain filter
    logger.info(
        "matcher.start",
        extra={
            "jobs_received": len(all_jobs),
            "role_domain_filtered": eliminated_role_domain,
            "jobs_after_filter": len(filtered_jobs),
            "active_domain": settings.ACTIVE_ROLE_DOMAIN,
            "user_skills_count": len(user_skills),
            "resume_id": str(resume.id)
        }
    )

    if not filtered_jobs:
        logger.info(
            "Job discovery: all jobs filtered by role domain",
            extra={
                "resume_id": str(resume.id),
                "jobs_eliminated": eliminated_role_domain,
                "active_domain": settings.ACTIVE_ROLE_DOMAIN
            }
        )
        return []

    # 2️⃣ INITIAL TITLE-BASED MATCHING (to identify top candidates for enrichment)
    # Match jobs to user skills - track elimination reasons
    initial_candidates = []
    match_scores = []

    # Elimination counters
    eliminated_no_content = 0
    eliminated_no_resume_skills = 0
    eliminated_no_job_skills = 0
    eliminated_no_skill_match = 0

    for job in filtered_jobs:
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

        # Job passed all filters - calculate initial title-based score
        match_count = len(matched_skills)
        # Score as percentage of job's required skills that user has
        match_percentage = int((match_count / len(job_skills_lower)) * 100)
        match_reason = ", ".join(sorted(skill.title() for skill in matched_skills))

        # Store candidate for potential enrichment
        initial_candidates.append({
            "job": job,  # Keep original job object for enrichment
            "id": str(job_id),
            "title": job_title,
            "company": company_name,
            "url": absolute_url,
            "location": location,
            "match_reason": match_reason,
            "match_percentage": match_percentage,
            "initial_score": match_percentage,  # Store title-based score
            "has_content": bool(job_content),
            "source": "greenhouse"
        })

    # 3️⃣ SELECTIVE ENRICHMENT: Fetch full descriptions for top N candidates
    # Sort candidates by initial score to identify top matches
    initial_candidates.sort(key=lambda x: x["initial_score"], reverse=True)

    enriched_count = 0
    enrichment_failed = 0
    candidates_to_enrich = initial_candidates[:settings.MAX_JOBS_TO_ENRICH]

    for candidate in candidates_to_enrich:
        if candidate["has_content"]:
            continue  # Already has content

        job_obj = candidate["job"]
        company_slug = job_obj.get("_company_slug")
        job_id = candidate["id"]

        enriched_job = _enrich_job_with_description(company_slug, job_id, job_obj)
        if enriched_job:
            # Re-extract skills from full description
            full_content = enriched_job.get("content", "")
            job_skills_full = _extract_skills_from_job(full_content)

            # Also include title skills
            title_skills = _infer_skills_from_title(candidate["title"])
            job_skills_full.update(title_skills)

            # Re-calculate match with full content
            job_skills_lower = set(skill.lower() for skill in job_skills_full)
            matched_skills = job_skills_lower.intersection(user_skills_set)

            if matched_skills:
                match_count = len(matched_skills)
                new_score = int((match_count / len(job_skills_lower)) * 100) if job_skills_lower else 0
                new_reason = ", ".join(sorted(skill.title() for skill in matched_skills))

                # Update candidate with enriched data
                candidate["match_percentage"] = new_score
                candidate["match_reason"] = new_reason
                candidate["has_content"] = True
                candidate["enriched"] = True
                enriched_count += 1
            else:
                # Lost match after enrichment (initial match was weak)
                enrichment_failed += 1
        else:
            enrichment_failed += 1

    logger.info(
        "matcher.enrichment",
        extra={
            "candidates_total": len(initial_candidates),
            "candidates_enriched": enriched_count,
            "enrichment_failed": enrichment_failed,
            "max_to_enrich": settings.MAX_JOBS_TO_ENRICH
        }
    )

    # 4️⃣ SCORING GUARDRAILS: Cap scores for title-only matches
    matched_jobs = []
    for candidate in initial_candidates:
        score = candidate["match_percentage"]

        # Apply score cap if no full content
        if not candidate.get("has_content", False):
            score = min(score, settings.TITLE_ONLY_SCORE_CAP)
            candidate["match_percentage"] = score
            candidate["title_only_match"] = True

        # Only include if still has match after enrichment/capping
        if score > 0:
            # Build final job dict for response
            matched_jobs.append({
                "id": candidate["id"],
                "title": candidate["title"],
                "company": candidate["company"],
                "url": candidate["url"],
                "location": candidate["location"],
                "match_reason": candidate["match_reason"],
                "match_percentage": score,
                "description": candidate["job"].get("content", "")[:200] + "..." if candidate["job"].get("content") else "",
                "source": candidate["source"]
            })

    # 2️⃣ Log: Score distribution (after enrichment and guardrails)
    if matched_jobs:
        scores = [j["match_percentage"] for j in matched_jobs]
        logger.info(
            "matcher.scores",
            extra={
                "min": min(scores),
                "max": max(scores),
                "avg": sum(scores) / len(scores),
                "enriched_count": enriched_count
            }
        )
    else:
        logger.info("matcher.scores", extra={"status": "unavailable"})

    # 3️⃣ Log: Elimination reasons (counts)
    logger.info(
        "matcher.filtered",
        extra={
            "role_domain": eliminated_role_domain,
            "no_content": eliminated_no_content,
            "no_resume_skills": eliminated_no_resume_skills,
            "no_job_skills": eliminated_no_job_skills,
            "no_skill_match": eliminated_no_skill_match
        }
    )

    # Sort by location priority, then match percentage
    def location_priority(job):
        """
        Prioritize jobs by location: USA/Remote first, then international.
        Returns tuple: (location_score, match_percentage) for multi-level sorting.
        """
        location = job.get("location", "").lower()

        # Priority 1: USA + Remote
        if "remote" in location and ("usa" in location or "united states" in location or "us" in location):
            return (3, job["match_percentage"])

        # Priority 2: USA locations
        if "usa" in location or "united states" in location or "us" in location or any(
            state in location for state in ["california", "new york", "texas", "washington", "massachusetts"]
        ):
            return (2, job["match_percentage"])

        # Priority 3: Remote (any location)
        if "remote" in location:
            return (1, job["match_percentage"])

        # Priority 4: International
        return (0, job["match_percentage"])

    matched_jobs.sort(key=location_priority, reverse=True)

    # 4️⃣ Log: Final output count
    logger.info(
        "matcher.result",
        extra={
            "count": len(matched_jobs),
            "resume_id": str(resume.id)
        }
    )

    return matched_jobs
