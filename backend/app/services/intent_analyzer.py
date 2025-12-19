"""
Resume Intent Analyzer Service

Analyzes resumes to extract career intent profiles that inform job matching.
Goes beyond skills to understand what kind of role the candidate is targeting.
"""

import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from ..services.analysis.llm_client import LLMClient, LLMSettings

logger = logging.getLogger(__name__)


class IntentProfile:
    """Structured representation of resume career intent"""

    def __init__(
        self,
        primary_archetype: str,
        archetype_confidence: float,
        secondary_archetypes: List[str],
        work_orientation: Dict[str, float],
        soft_deprioritize: List[str],
        reasoning: str
    ):
        self.primary_archetype = primary_archetype
        self.archetype_confidence = archetype_confidence
        self.secondary_archetypes = secondary_archetypes
        self.work_orientation = work_orientation
        self.soft_deprioritize = soft_deprioritize
        self.reasoning = reasoning

    def to_dict(self) -> dict:
        return {
            "primary_archetype": self.primary_archetype,
            "archetype_confidence": self.archetype_confidence,
            "secondary_archetypes": self.secondary_archetypes,
            "work_orientation": self.work_orientation,
            "soft_deprioritize": self.soft_deprioritize,
            "reasoning": self.reasoning
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntentProfile":
        return cls(
            primary_archetype=data["primary_archetype"],
            archetype_confidence=data["archetype_confidence"],
            secondary_archetypes=data["secondary_archetypes"],
            work_orientation=data["work_orientation"],
            soft_deprioritize=data["soft_deprioritize"],
            reasoning=data["reasoning"]
        )


class IntentAnalyzer:
    """Analyzes resume to extract career intent profile"""

    # Core role archetypes (industry-agnostic)
    ROLE_ARCHETYPES = [
        "solutions_engineer",
        "integration_engineer",
        "systems_engineer",
        "platform_engineer",
        "product_engineer",
        "frontend_engineer",
        "backend_engineer",
        "fullstack_engineer",
        "data_engineer",
        "ml_engineer",
        "devops_engineer",
        "security_engineer",
        "mobile_engineer",
        "embedded_engineer",
        "analyst",
        "strategist",
        "technical_lead",
        "engineering_manager",
        "product_manager",
        "technical_writer"
    ]

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize intent analyzer

        Args:
            llm_client: Optional LLM client. If not provided, creates default.
        """
        self.llm_client = llm_client or LLMClient(LLMSettings())

    def analyze_resume_intent(
        self,
        resume_data: dict,
        db: Session,
        resume_id: str
    ) -> IntentProfile:
        """
        Analyze resume to extract career intent profile

        Args:
            resume_data: Dict with skills, experience, education
            db: Database session
            resume_id: Resume UUID for caching

        Returns:
            IntentProfile with archetype, orientation, and signals
        """
        logger.info(f"Analyzing intent for resume {resume_id}")

        # Check cache first
        cached_profile = self._get_cached_profile(db, resume_id)
        if cached_profile:
            logger.info(f"Using cached intent profile for resume {resume_id}")
            return cached_profile

        # Build LLM prompt
        prompt = self._build_intent_prompt(resume_data)

        # Call LLM
        try:
            response = self.llm_client.analyze(prompt)
            profile = self._parse_intent_response(response)

            # Cache result
            self._cache_profile(db, resume_id, profile)

            logger.info(
                f"Intent analysis complete for {resume_id}: "
                f"{profile.primary_archetype} ({profile.archetype_confidence:.2f})"
            )

            return profile

        except Exception as e:
            logger.error(f"Intent analysis failed for {resume_id}: {e}")
            # Return default profile on error
            return self._default_profile()

    def _build_intent_prompt(self, resume_data: dict) -> str:
        """Build LLM prompt for intent extraction"""

        # Extract resume components
        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience", [])
        education = resume_data.get("education", [])
        summary = resume_data.get("summary", "")

        # Format experience entries
        experience_text = ""
        for i, exp in enumerate(experience[:5], 1):
            experience_text += f"\n{i}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}"
            experience_text += f"\n   Duration: {exp.get('duration', 'N/A')}"
            description = exp.get('description', '')
            if description:
                # Truncate long descriptions
                desc_preview = description[:300] + "..." if len(description) > 300 else description
                experience_text += f"\n   {desc_preview}"

        # Format skills
        skills_text = ", ".join(skills[:50]) if skills else "Not specified"

        # Format education
        education_text = ""
        for edu in education:
            education_text += f"\n- {edu.get('degree', 'N/A')} from {edu.get('institution', 'N/A')}"

        prompt = f"""You are a career intent analyzer. Your job is to understand what kind of role this resume is TARGETING, not just what skills it contains.

RESUME DATA:

Summary:
{summary if summary else "Not provided"}

Skills:
{skills_text}

Experience:
{experience_text}

Education:
{education_text if education_text else "Not specified"}

ANALYSIS TASK:

Analyze this resume and determine:

1. **Primary Role Archetype**: What is the ONE dominant role type this person is targeting?
   Choose from: {', '.join(self.ROLE_ARCHETYPES)}

2. **Archetype Confidence**: How confident are you? (0.0 to 1.0)
   - 0.9-1.0: Very clear signal
   - 0.7-0.9: Strong signal
   - 0.5-0.7: Moderate signal
   - Below 0.5: Unclear/ambiguous

3. **Secondary Archetypes**: What are 1-3 adjacent roles? (Ranked by fit)

4. **Work Orientation**: Score these dimensions (0.0 to 1.0):
   - customer_facing: How much does the work involve direct customer/client interaction?
   - cross_system: Does the work involve integrating multiple systems vs single-domain focus?
   - integration_heavy: Is this about connecting things vs building greenfield?
   - product_adjacent: Does the work touch product decisions vs pure infrastructure?
   - hands_on_technical: Does the role involve writing code vs managing/strategizing?
   - external_communication: Does the role require communicating technical concepts to non-technical stakeholders?

5. **Soft Deprioritize**: Which role types should be de-weighted? (Not excluded, just ranked lower)
   Examples: strategy_only, analytics_only, management_only, sales_oriented, non_technical

6. **Reasoning**: Brief explanation (2-3 sentences) of why you chose this primary archetype

IMPORTANT GUIDELINES:
- Look at job titles, responsibilities, and progression - not just skills
- A Solutions Engineer with customer-facing experience is NOT a Platform Engineer
- Someone who "integrated" systems is different from someone who "built" them
- Pay attention to verbs: "implemented", "architected", "collaborated with customers", "drove adoption"
- Industry doesn't matter - focus on work patterns
- Senior ICs are not managers unless titles/duties clearly indicate people management
- Don't be swayed by buzzwords - focus on actual work done

Return ONLY valid JSON:
{{
  "primary_archetype": "<archetype>",
  "archetype_confidence": <float>,
  "secondary_archetypes": ["<archetype1>", "<archetype2>"],
  "work_orientation": {{
    "customer_facing": <float>,
    "cross_system": <float>,
    "integration_heavy": <float>,
    "product_adjacent": <float>,
    "hands_on_technical": <float>,
    "external_communication": <float>
  }},
  "soft_deprioritize": ["<category1>", "<category2>"],
  "reasoning": "<brief explanation>"
}}
"""
        return prompt

    def _parse_intent_response(self, response: str) -> IntentProfile:
        """Parse LLM response into IntentProfile"""

        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parse JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent response: {e}\nResponse: {response}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

        # Validate required fields
        required_fields = [
            "primary_archetype",
            "archetype_confidence",
            "secondary_archetypes",
            "work_orientation",
            "soft_deprioritize",
            "reasoning"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Validate archetype
        if data["primary_archetype"] not in self.ROLE_ARCHETYPES:
            logger.warning(
                f"Unknown archetype '{data['primary_archetype']}', "
                f"using fullstack_engineer as fallback"
            )
            data["primary_archetype"] = "fullstack_engineer"

        # Validate confidence
        confidence = float(data["archetype_confidence"])
        if not (0.0 <= confidence <= 1.0):
            logger.warning(f"Confidence {confidence} out of range, clamping to [0, 1]")
            confidence = max(0.0, min(1.0, confidence))

        # Validate work orientation
        work_orientation = data["work_orientation"]
        for key in work_orientation:
            work_orientation[key] = max(0.0, min(1.0, float(work_orientation[key])))

        return IntentProfile(
            primary_archetype=data["primary_archetype"],
            archetype_confidence=confidence,
            secondary_archetypes=data["secondary_archetypes"][:3],  # Limit to 3
            work_orientation=work_orientation,
            soft_deprioritize=data["soft_deprioritize"],
            reasoning=data["reasoning"]
        )

    def _default_profile(self) -> IntentProfile:
        """Return default profile when analysis fails"""
        return IntentProfile(
            primary_archetype="fullstack_engineer",
            archetype_confidence=0.3,
            secondary_archetypes=[],
            work_orientation={
                "customer_facing": 0.5,
                "cross_system": 0.5,
                "integration_heavy": 0.5,
                "product_adjacent": 0.5,
                "hands_on_technical": 0.7,
                "external_communication": 0.5
            },
            soft_deprioritize=[],
            reasoning="Default profile due to analysis error"
        )

    def _get_cached_profile(
        self,
        db: Session,
        resume_id: str
    ) -> Optional[IntentProfile]:
        """Retrieve cached intent profile from database"""
        try:
            from ..db.models.resume import Resume

            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return None

            # Check if intent_profile exists
            if not hasattr(resume, 'intent_profile') or not resume.intent_profile:
                return None

            return IntentProfile.from_dict(resume.intent_profile)

        except Exception as e:
            logger.warning(f"Failed to retrieve cached profile: {e}")
            return None

    def _cache_profile(
        self,
        db: Session,
        resume_id: str,
        profile: IntentProfile
    ) -> None:
        """Cache intent profile in database"""
        try:
            from ..db.models.resume import Resume

            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if resume:
                resume.intent_profile = profile.to_dict()
                db.commit()
                logger.info(f"Cached intent profile for resume {resume_id}")
            else:
                logger.warning(f"Resume {resume_id} not found for caching")

        except Exception as e:
            logger.error(f"Failed to cache intent profile: {e}")
            db.rollback()


def score_intent_alignment(
    job_title: str,
    job_description: str,
    intent_profile: IntentProfile
) -> Dict[str, float]:
    """
    Score how well a job aligns with resume intent

    Args:
        job_title: Job title
        job_description: Job description text
        intent_profile: Resume intent profile

    Returns:
        Dict with alignment_score (0-100) and component scores
    """

    # Normalize inputs
    title_lower = job_title.lower()
    desc_lower = job_description.lower() if job_description else ""
    combined_text = f"{title_lower} {desc_lower}"

    # Component scores
    archetype_score = 0.0
    orientation_score = 0.0
    deprioritization_penalty = 0.0

    # 1. Primary archetype matching (40% weight)
    archetype_keywords = _get_archetype_keywords(intent_profile.primary_archetype)
    archetype_matches = sum(1 for kw in archetype_keywords if kw in combined_text)

    if archetype_matches > 0:
        # Scale by confidence
        archetype_score = (
            min(archetype_matches / len(archetype_keywords), 1.0) *
            intent_profile.archetype_confidence *
            40
        )

    # 2. Secondary archetype partial credit (10% weight)
    for secondary in intent_profile.secondary_archetypes[:2]:
        secondary_keywords = _get_archetype_keywords(secondary)
        secondary_matches = sum(1 for kw in secondary_keywords if kw in combined_text)
        if secondary_matches > 0:
            archetype_score += min(secondary_matches / len(secondary_keywords), 1.0) * 5

    # 3. Work orientation alignment (30% weight)
    orientation_signals = {
        "customer_facing": [
            "customer", "client", "stakeholder", "external",
            "customer-facing", "client-facing", "solutions"
        ],
        "cross_system": [
            "integration", "integrate", "cross-functional", "multiple systems",
            "interoperability", "api", "connector"
        ],
        "integration_heavy": [
            "integrate", "integration", "connector", "middleware",
            "bridge", "orchestration", "data pipeline"
        ],
        "product_adjacent": [
            "product", "feature", "user experience", "roadmap",
            "product-facing", "user-centric"
        ],
        "hands_on_technical": [
            "develop", "build", "code", "implement", "engineer",
            "programming", "software development"
        ],
        "external_communication": [
            "present", "communicate", "collaborate", "evangelize",
            "technical writing", "documentation"
        ]
    }

    for orientation_key, keywords in orientation_signals.items():
        user_score = intent_profile.work_orientation.get(orientation_key, 0.5)

        # Count keyword matches in job
        job_matches = sum(1 for kw in keywords if kw in combined_text)
        job_score = min(job_matches / len(keywords), 1.0)

        # Alignment is high when both are high or both are low
        alignment = 1.0 - abs(user_score - job_score)
        orientation_score += alignment * 5  # 6 orientations * 5 = 30 points max

    # 4. Soft deprioritization penalties (up to -20% penalty)
    deprioritization_keywords = {
        "strategy_only": ["strategy", "strategic planning", "business strategy"],
        "analytics_only": ["analytics", "analyst", "reporting", "business intelligence"],
        "management_only": ["manager", "director", "vp", "head of", "people management"],
        "sales_oriented": ["sales", "business development", "account executive", "revenue"],
        "non_technical": ["non-technical", "administrative", "coordinator"]
    }

    for category in intent_profile.soft_deprioritize:
        if category in deprioritization_keywords:
            keywords = deprioritization_keywords[category]
            matches = sum(1 for kw in keywords if kw in combined_text)
            if matches > 0:
                deprioritization_penalty += min(matches * 5, 20)  # Max -20 penalty

    # 5. Calculate final alignment score (0-100)
    base_score = archetype_score + orientation_score
    final_score = max(0, min(100, base_score - deprioritization_penalty))

    return {
        "alignment_score": final_score,
        "archetype_score": archetype_score,
        "orientation_score": orientation_score,
        "deprioritization_penalty": deprioritization_penalty,
        "confidence": intent_profile.archetype_confidence
    }


def _get_archetype_keywords(archetype: str) -> List[str]:
    """Get keywords associated with a role archetype"""

    keyword_map = {
        "solutions_engineer": [
            "solutions engineer", "solution engineer", "solutions architect",
            "customer solutions", "technical solutions", "presales"
        ],
        "integration_engineer": [
            "integration engineer", "integration specialist", "api engineer",
            "middleware", "connector", "interoperability"
        ],
        "systems_engineer": [
            "systems engineer", "system engineer", "infrastructure engineer",
            "linux", "distributed systems", "reliability"
        ],
        "platform_engineer": [
            "platform engineer", "platform", "infrastructure platform",
            "internal tools", "developer experience", "devex"
        ],
        "product_engineer": [
            "product engineer", "product-focused", "product development",
            "user-facing", "feature development"
        ],
        "frontend_engineer": [
            "frontend", "front-end", "front end", "ui engineer",
            "react", "vue", "angular", "web development"
        ],
        "backend_engineer": [
            "backend", "back-end", "back end", "server-side",
            "api development", "microservices", "distributed systems"
        ],
        "fullstack_engineer": [
            "fullstack", "full-stack", "full stack",
            "frontend and backend", "end-to-end"
        ],
        "data_engineer": [
            "data engineer", "data pipeline", "etl", "data infrastructure",
            "data warehouse", "big data"
        ],
        "ml_engineer": [
            "ml engineer", "machine learning engineer", "mlops",
            "ai engineer", "deep learning"
        ],
        "devops_engineer": [
            "devops", "site reliability", "sre", "ci/cd",
            "automation", "infrastructure as code"
        ],
        "security_engineer": [
            "security engineer", "cybersecurity", "infosec",
            "application security", "penetration testing"
        ],
        "mobile_engineer": [
            "mobile engineer", "ios", "android", "mobile development",
            "react native", "flutter"
        ],
        "embedded_engineer": [
            "embedded", "firmware", "iot", "hardware",
            "embedded systems", "microcontrollers"
        ],
        "analyst": [
            "analyst", "business analyst", "data analyst",
            "analytics", "reporting"
        ],
        "strategist": [
            "strategist", "strategy", "strategic planning",
            "business strategy", "technical strategy"
        ],
        "technical_lead": [
            "tech lead", "technical lead", "lead engineer",
            "staff engineer", "principal engineer"
        ],
        "engineering_manager": [
            "engineering manager", "manager", "team lead",
            "people management", "director"
        ],
        "product_manager": [
            "product manager", "pm", "product management",
            "product owner", "product strategy"
        ],
        "technical_writer": [
            "technical writer", "documentation", "documentation engineer",
            "developer advocate", "content engineer"
        ]
    }

    return keyword_map.get(archetype, [archetype.replace("_", " ")])
