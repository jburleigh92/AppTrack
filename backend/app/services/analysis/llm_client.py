import json
import logging
import os
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LLMSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.2
    max_tokens: int = 1500
    api_key: Optional[str] = None


class LLMClient:
    def __init__(self, settings: LLMSettings):
        self.settings = settings
        self.provider = settings.provider.lower()
        self.model = settings.model
        
        if self.provider == "openai":
            try:
                import openai
                self.client = openai.AsyncOpenAI(api_key=settings.api_key or os.getenv("OPENAI_API_KEY"))
            except ImportError:
                logger.warning("OpenAI SDK not installed, LLM calls will fail")
                self.client = None
        elif self.provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=settings.api_key or os.getenv("ANTHROPIC_API_KEY"))
            except ImportError:
                logger.warning("Anthropic SDK not installed, LLM calls will fail")
                self.client = None
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def analyze_job_vs_resume(
        self,
        job_description: str,
        job_requirements: Optional[str],
        resume_summary: Optional[str],
        resume_skills: List[str],
        resume_experience: List[dict],
        resume_education: List[dict],
    ) -> dict:
        """
        Calls the LLM and returns a parsed dict with analysis results.
        
        Returns:
            dict with keys: match_score, matched_qualifications, missing_qualifications,
                          skill_suggestions, model_used, tokens_used
        """
        if not self.client:
            raise RuntimeError(f"{self.provider} SDK not available")
        
        prompt = self._build_prompt(
            job_description=job_description,
            job_requirements=job_requirements,
            resume_summary=resume_summary,
            resume_skills=resume_skills,
            resume_experience=resume_experience,
            resume_education=resume_education
        )
        
        try:
            if self.provider == "openai":
                response = await self._call_openai(prompt)
            elif self.provider == "anthropic":
                response = await self._call_anthropic(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            parsed = self._parse_response(response)
            parsed["model_used"] = self.model
            
            return parsed
        
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}", exc_info=True)
            raise
    
    def _build_prompt(
        self,
        job_description: str,
        job_requirements: Optional[str],
        resume_summary: Optional[str],
        resume_skills: List[str],
        resume_experience: List[dict],
        resume_education: List[dict]
    ) -> str:
        """Build the analysis prompt."""
        prompt = """You are a job application analyzer. Compare the candidate's resume against a job posting and provide a structured analysis.

JOB POSTING:
---
Description:
{job_description}

{job_requirements_section}
---

CANDIDATE RESUME:
---
{resume_summary_section}

Skills:
{skills_list}

Experience:
{experience_list}

Education:
{education_list}
---

Analyze the match between this resume and job posting. Return ONLY valid JSON with this exact structure:

{{
  "match_score": <integer 0-100>,
  "matched_qualifications": [<list of qualification strings the candidate meets>],
  "missing_qualifications": [<list of qualification strings the candidate lacks>],
  "skill_suggestions": [<list of specific skills the candidate should highlight or develop>]
}}

Guidelines:
- match_score: 0-100 where 100 is perfect match
- matched_qualifications: specific requirements from job posting that candidate meets
- missing_qualifications: specific requirements from job posting that candidate lacks
- skill_suggestions: actionable skills to learn or emphasize

Return ONLY the JSON object, no other text.
"""
        
        job_requirements_section = ""
        if job_requirements:
            job_requirements_section = f"Requirements:\n{job_requirements}"
        
        resume_summary_section = ""
        if resume_summary:
            resume_summary_section = f"Summary:\n{resume_summary}\n"
        
        skills_list = "\n".join(f"- {skill}" for skill in resume_skills) if resume_skills else "None listed"
        
        experience_list = []
        for exp in resume_experience:
            title = exp.get("title", "Unknown")
            company = exp.get("company", "Unknown")
            description = exp.get("description", "")
            experience_list.append(f"- {title} at {company}: {description}")
        experience_list = "\n".join(experience_list) if experience_list else "None listed"
        
        education_list = []
        for edu in resume_education:
            degree = edu.get("degree", "Unknown")
            institution = edu.get("institution", "Unknown")
            education_list.append(f"- {degree} from {institution}")
        education_list = "\n".join(education_list) if education_list else "None listed"
        
        return prompt.format(
            job_description=job_description[:2000],
            job_requirements_section=job_requirements_section[:1000] if job_requirements else "",
            resume_summary_section=resume_summary_section,
            skills_list=skills_list[:1000],
            experience_list=experience_list[:2000],
            education_list=education_list[:1000]
        )
    
    async def _call_openai(self, prompt: str) -> dict:
        """Call OpenAI API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a precise job application analyzer. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else None
        
        return {
            "content": content,
            "tokens_used": tokens_used
        }
    
    async def _call_anthropic(self, prompt: str) -> dict:
        """Call Anthropic API."""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.settings.max_tokens,
            temperature=self.settings.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else None
        
        return {
            "content": content,
            "tokens_used": tokens_used
        }
    
    def _parse_response(self, response: dict) -> dict:
        """Parse and validate LLM response."""
        content = response["content"]
        tokens_used = response.get("tokens_used")
        
        # Try to extract JSON from response
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {content[:200]}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
        
        # Validate required fields
        required_fields = ["match_score", "matched_qualifications", "missing_qualifications", "skill_suggestions"]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field in LLM response: {field}")
        
        # Validate types
        if not isinstance(parsed["match_score"], int):
            parsed["match_score"] = int(parsed["match_score"])
        
        if not 0 <= parsed["match_score"] <= 100:
            raise ValueError(f"match_score out of range: {parsed['match_score']}")
        
        for list_field in ["matched_qualifications", "missing_qualifications", "skill_suggestions"]:
            if not isinstance(parsed[list_field], list):
                raise ValueError(f"{list_field} must be a list")
        
        parsed["tokens_used"] = tokens_used
        
        return parsed
