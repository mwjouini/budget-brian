"""Matching engine for scoring job relevance based on configurable keywords and rules."""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple
from app.config import get_keywords_config
from app.utils.text import clean_html, normalize_string


@dataclass
class MatchResult:
    """Outcome of job relevance evaluation."""
    score: float
    category: str  # 'strong', 'medium', 'weak', 'not_relevant'
    reasons: List[Dict[str, Any]] = field(default_factory=list)
    is_alert_worthy: bool = False


class MatchingEngine:
    """Evaluates job listings against target entities, keywords, and geographic constraints."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        raw_config = config or get_keywords_config()
        self.entities = raw_config.get("entities", {})
        self.scoring = raw_config.get("scoring", {})
        self.weights = self.scoring.get("weights", {
            "role_in_title_exact": 45,
            "role_in_title_variation": 30,
            "role_in_desc_exact": 25,
            "role_in_desc_variation": 15,
            "org_primary": 40,
            "org_generic": 25,
            "geo_primary": 25,
            "geo_secondary": 15,
            "regulator_match": 25,
        })
        self.thresholds = self.scoring.get("thresholds", {
            "strong": 85,
            "medium": 60,
            "weak": 30,
        })
        self.negative_keywords = self.scoring.get("negative_keywords", [])

    def _matches_any(self, text: str, patterns: List[str], exact_word_boundary: bool = True) -> Optional[str]:
        """Check if any of the patterns match inside text."""
        norm_text = f" {text} "
        for pattern in patterns:
            norm_pattern = normalize_string(pattern)
            if not norm_pattern:
                continue
            if exact_word_boundary:
                # Use regex with word boundary for accuracy
                escaped = re.escape(norm_pattern)
                if re.search(rf"\b{escaped}\b", norm_text, re.IGNORECASE):
                    return pattern
            else:
                if norm_pattern in norm_text:
                    return pattern
        return None

    def evaluate(
        self,
        title: str,
        company: str,
        location: Optional[str] = None,
        description: Optional[str] = None,
    ) -> MatchResult:
        """
        Score a job advertisement based on role, organisation, geography, and regulator rules.
        """
        title_norm = normalize_string(title)
        company_norm = normalize_string(company)
        location_norm = normalize_string(location or "")
        desc_clean = clean_html(description or "")
        desc_norm = normalize_string(desc_clean)

        combined_text = f"{title_norm} {company_norm} {location_norm} {desc_norm}"

        reasons: List[Dict[str, Any]] = []
        raw_score: float = 0.0

        # 0. Check Negative Keywords (e.g. Cook, Chef, Veterinary, Retail Manager)
        for neg in self.negative_keywords:
            if self._matches_any(title_norm, [neg]):
                return MatchResult(
                    score=0.0,
                    category="not_relevant",
                    reasons=[{
                        "rule": "NEGATIVE_TITLE_DISQUALIFIED",
                        "description": f"Excluded due to negative keyword: '{neg}'",
                        "points": 0.0,
                    }],
                    is_alert_worthy=False,
                )

        # 1. Role Matching
        role_cfg = self.entities.get("role", {})
        exact_title_match = self._matches_any(title_norm, role_cfg.get("exact_title_matches", ["Registered Manager"]))
        variation_title_match = self._matches_any(title_norm, role_cfg.get("variations", []))

        role_matched = False
        if exact_title_match:
            pts = float(self.weights.get("role_in_title_exact", 45))
            raw_score += pts
            role_matched = True
            reasons.append({
                "rule": "ROLE_TITLE_EXACT",
                "description": f"Target role '{exact_title_match}' matched in job title",
                "points": pts,
            })
        elif variation_title_match:
            pts = float(self.weights.get("role_in_title_variation", 30))
            raw_score += pts
            role_matched = True
            reasons.append({
                "rule": "ROLE_TITLE_VARIATION",
                "description": f"Role variation '{variation_title_match}' matched in job title",
                "points": pts,
            })
        else:
            # Check description for role
            exact_desc_match = self._matches_any(desc_norm, role_cfg.get("exact_title_matches", ["Registered Manager"]))
            if exact_desc_match:
                pts = float(self.weights.get("role_in_desc_exact", 25))
                raw_score += pts
                role_matched = True
                reasons.append({
                    "rule": "ROLE_DESC_EXACT",
                    "description": f"Target role '{exact_desc_match}' referenced in description",
                    "points": pts,
                })
            else:
                var_desc_match = self._matches_any(desc_norm, role_cfg.get("variations", []))
                if var_desc_match:
                    pts = float(self.weights.get("role_in_desc_variation", 15))
                    raw_score += pts
                    reasons.append({
                        "rule": "ROLE_DESC_VARIATION",
                        "description": f"Role variation '{var_desc_match}' referenced in description",
                        "points": pts,
                    })

        # 2. Organisation Matching
        org_cfg = self.entities.get("organisation", {})
        org_search_space = f"{company_norm} {title_norm} {desc_norm}"

        primary_org_match = self._matches_any(org_search_space, org_cfg.get("primary", []))
        generic_org_match = self._matches_any(org_search_space, org_cfg.get("generic", []))

        org_matched = False
        if primary_org_match:
            pts = float(self.weights.get("org_primary", 40))
            raw_score += pts
            org_matched = True
            reasons.append({
                "rule": "ORG_PRIMARY",
                "description": f"Primary organisation matched: '{primary_org_match}'",
                "points": pts,
            })
        elif generic_org_match:
            pts = float(self.weights.get("org_generic", 25))
            raw_score += pts
            org_matched = True
            reasons.append({
                "rule": "ORG_GENERIC",
                "description": f"Generic organisation matched: '{generic_org_match}'",
                "points": pts,
            })

        # 3. Geography Matching (Northern Ireland / Belfast)
        geo_cfg = self.entities.get("geography", {})
        geo_search_space = f"{location_norm} {title_norm} {desc_norm}"

        primary_geo_match = self._matches_any(geo_search_space, geo_cfg.get("primary", ["Northern Ireland", "Belfast"]))
        secondary_geo_match = self._matches_any(geo_search_space, geo_cfg.get("counties_and_towns", []))
        
        # Check BT postcode in location
        has_bt_postcode = bool(re.search(r"\bbt\d{1,2}\b", location_norm))

        geo_matched = False
        if primary_geo_match:
            pts = float(self.weights.get("geo_primary", 25))
            raw_score += pts
            geo_matched = True
            reasons.append({
                "rule": "GEO_PRIMARY",
                "description": f"Target location matched: '{primary_geo_match}'",
                "points": pts,
            })
        elif secondary_geo_match or has_bt_postcode:
            loc_label = secondary_geo_match or "BT Postcode"
            pts = float(self.weights.get("geo_secondary", 15))
            raw_score += pts
            geo_matched = True
            reasons.append({
                "rule": "GEO_SECONDARY",
                "description": f"Northern Ireland regional location matched: '{loc_label}'",
                "points": pts,
            })

        # 4. Regulator Matching (RQIA)
        reg_cfg = self.entities.get("regulator", {})
        reg_search_space = f"{desc_norm} {title_norm}"
        regulator_match = self._matches_any(reg_search_space, reg_cfg.get("exact", ["RQIA"]))

        if regulator_match:
            pts = float(self.weights.get("regulator_match", 25))
            raw_score += pts
            reasons.append({
                "rule": "REGULATOR_RQIA",
                "description": f"Northern Ireland regulator matched: '{regulator_match}'",
                "points": pts,
            })

        # Clamp score between 0.0 and 100.0
        final_score = max(0.0, min(100.0, raw_score))

        # Enforce specification rules from ANTIGRAVITY_TASK.md Section 2:
        # Strong match (>= 85): core role + organisation or regulator + relevant location
        # Medium match (60-84): core role + relevant location, but organisation uncertain
        # Weak match (30-59): organisation match without clear Registered Manager role
        # Not relevant (< 30): everything else
        if org_matched:
            if role_matched:
                if geo_matched or regulator_match:
                    final_score = max(85.0, min(100.0, raw_score))
                else:
                    final_score = max(70.0, min(84.0, raw_score))
            else:
                # Vivid Healthcare mentioned, but not a Registered Manager role -> Weak match (30-59)
                final_score = max(30.0, min(55.0, raw_score))
        else:
            if role_matched and geo_matched:
                # Core role + relevant location (Belfast / NI), organisation uncertain -> Medium match (60-84)
                final_score = max(60.0, min(80.0, raw_score))
            elif role_matched and regulator_match:
                final_score = max(60.0, min(75.0, raw_score))
            else:
                # Unrelated organisation or missing core role
                final_score = min(25.0, raw_score)

        # Categorisation logic
        # Strong (>=85): core role + (organisation or regulator) + relevant location
        # Medium (60-84): core role + location, even if org is uncertain
        # Weak (30-59): org match without clear Registered Manager, or Registered Manager with weak geo
        # Not relevant (<30)
        strong_thresh = self.thresholds.get("strong", 85)
        med_thresh = self.thresholds.get("medium", 60)
        weak_thresh = self.thresholds.get("weak", 30)

        if final_score >= strong_thresh:
            category = "strong"
        elif final_score >= med_thresh:
            category = "medium"
        elif final_score >= weak_thresh:
            category = "weak"
        else:
            category = "not_relevant"

        # Alert worthy if score >= medium threshold (60)
        is_alert_worthy = final_score >= med_thresh

        return MatchResult(
            score=round(final_score, 1),
            category=category,
            reasons=reasons,
            is_alert_worthy=is_alert_worthy,
        )


# Global matching engine instance
matching_engine = MatchingEngine()
