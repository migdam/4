"""
Enhancement 1-2: Advanced Skills Matching with Synonyms and Semantic Similarity
"""
from typing import List, Set, Dict
import re
from difflib import SequenceMatcher


class SkillsMatcher:
    """Advanced skill matching with synonyms and semantic similarity"""

    # Comprehensive skill synonym mapping
    SKILL_SYNONYMS = {
        'javascript': ['js', 'ecmascript', 'es6', 'es2015', 'node.js', 'nodejs'],
        'typescript': ['ts'],
        'python': ['py', 'python3'],
        'react': ['reactjs', 'react.js'],
        'vue': ['vuejs', 'vue.js'],
        'angular': ['angularjs', 'angular.js'],
        'postgresql': ['postgres', 'psql', 'pg'],
        'mongodb': ['mongo'],
        'kubernetes': ['k8s'],
        'docker': ['containerization'],
        'aws': ['amazon web services'],
        'gcp': ['google cloud platform', 'google cloud'],
        'azure': ['microsoft azure'],
        'machine learning': ['ml', 'ai', 'artificial intelligence'],
        'deep learning': ['dl', 'neural networks'],
        'natural language processing': ['nlp'],
        'continuous integration': ['ci', 'ci/cd', 'continuous deployment'],
        'test driven development': ['tdd'],
        'object oriented programming': ['oop'],
        'functional programming': ['fp'],
        'rest api': ['restful', 'rest', 'api'],
        'graphql': ['gql'],
        'sql': ['structured query language'],
        'nosql': ['non-sql'],
        'git': ['version control', 'github', 'gitlab', 'bitbucket'],
        'agile': ['scrum', 'kanban'],
        'devops': ['dev ops'],
        'frontend': ['front-end', 'front end'],
        'backend': ['back-end', 'back end'],
        'fullstack': ['full-stack', 'full stack'],
    }

    # Skill categories for broader matching
    SKILL_CATEGORIES = {
        'web_frontend': ['javascript', 'typescript', 'react', 'vue', 'angular', 'html', 'css', 'sass', 'less'],
        'web_backend': ['python', 'java', 'node.js', 'go', 'ruby', 'php', 'c#', '.net'],
        'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'dynamodb'],
        'cloud': ['aws', 'gcp', 'azure', 'heroku', 'digitalocean'],
        'devops': ['docker', 'kubernetes', 'jenkins', 'terraform', 'ansible', 'ci/cd'],
        'data_science': ['python', 'r', 'machine learning', 'deep learning', 'tensorflow', 'pytorch'],
        'mobile': ['react native', 'flutter', 'swift', 'kotlin', 'android', 'ios']
    }

    def __init__(self):
        self.synonym_map = self._build_synonym_map()

    def _build_synonym_map(self) -> Dict[str, Set[str]]:
        """Build a bidirectional synonym map"""
        synonym_map = {}

        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            # Add canonical skill
            all_forms = {canonical.lower()} | {s.lower() for s in synonyms}

            # Map each form to all other forms
            for form in all_forms:
                synonym_map[form] = all_forms

        return synonym_map

    def normalize_skill(self, skill: str) -> str:
        """Normalize a skill to its canonical form"""
        skill_lower = skill.lower().strip()

        # Find in synonyms
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            if skill_lower == canonical or skill_lower in [s.lower() for s in synonyms]:
                return canonical

        return skill_lower

    def get_skill_variants(self, skill: str) -> Set[str]:
        """Get all variants (synonyms) of a skill"""
        skill_lower = skill.lower().strip()
        return self.synonym_map.get(skill_lower, {skill_lower})

    def match_skills(
        self,
        candidate_skills: List[str],
        job_skills: List[str],
        match_mode: str = 'strict'  # 'strict', 'synonyms', 'fuzzy', 'semantic'
    ) -> Dict:
        """
        Match candidate skills against job requirements

        Returns:
            dict with matched_skills, missing_skills, extra_skills, match_score
        """
        candidate_normalized = set(self.normalize_skill(s) for s in candidate_skills)
        job_normalized = set(self.normalize_skill(s) for s in job_skills)

        if match_mode == 'strict':
            matched = candidate_normalized & job_normalized

        elif match_mode == 'synonyms':
            matched = set()
            for candidate_skill in candidate_normalized:
                variants = self.get_skill_variants(candidate_skill)
                for job_skill in job_normalized:
                    if job_skill in variants:
                        matched.add(candidate_skill)
                        break

        elif match_mode == 'fuzzy':
            matched = set()
            for candidate_skill in candidate_normalized:
                for job_skill in job_normalized:
                    # Use fuzzy string matching
                    similarity = SequenceMatcher(None, candidate_skill, job_skill).ratio()
                    if similarity > 0.8:  # 80% similarity threshold
                        matched.add(candidate_skill)
                        break

        elif match_mode == 'semantic':
            # Combine synonyms and fuzzy matching
            matched = set()
            for candidate_skill in candidate_normalized:
                variants = self.get_skill_variants(candidate_skill)
                for job_skill in job_normalized:
                    # Check synonyms
                    if job_skill in variants:
                        matched.add(candidate_skill)
                        break
                    # Check fuzzy match
                    similarity = SequenceMatcher(None, candidate_skill, job_skill).ratio()
                    if similarity > 0.75:
                        matched.add(candidate_skill)
                        break

        missing_skills = job_normalized - matched
        extra_skills = candidate_normalized - job_normalized

        match_score = len(matched) / len(job_normalized) if job_normalized else 0.0

        return {
            'matched_skills': list(matched),
            'missing_skills': list(missing_skills),
            'extra_skills': list(extra_skills),
            'match_score': match_score,
            'match_percentage': match_score * 100
        }

    def get_skill_category(self, skill: str) -> List[str]:
        """Get categories that contain this skill"""
        skill_normalized = self.normalize_skill(skill)
        categories = []

        for category, skills in self.SKILL_CATEGORIES.items():
            normalized_category_skills = [self.normalize_skill(s) for s in skills]
            if skill_normalized in normalized_category_skills:
                categories.append(category)

        return categories

    def suggest_related_skills(self, skills: List[str]) -> List[str]:
        """Suggest related skills based on current skills"""
        categories = set()
        for skill in skills:
            skill_categories = self.get_skill_category(skill)
            categories.update(skill_categories)

        # Get all skills from these categories
        related_skills = set()
        for category in categories:
            category_skills = self.SKILL_CATEGORIES.get(category, [])
            related_skills.update(category_skills)

        # Remove skills already known
        normalized_known = {self.normalize_skill(s) for s in skills}
        suggestions = [s for s in related_skills if self.normalize_skill(s) not in normalized_known]

        return suggestions[:10]  # Top 10 suggestions
