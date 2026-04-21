import logging

from entities.views.base_view import BaseEntityViewSet
from entities.okta_entities.reviews.review_models import Review
from entities.okta_entities.reviews.review_serializers import ReviewSerializer

logger = logging.getLogger(__name__)


class ReviewViewSet(BaseEntityViewSet):
    okta_endpoint = "/governance/api/v1/reviews"
    entity_type = "reviews"
    serializer_class = ReviewSerializer
    model = Review

    def extract_data(self, okta_data):
        items = okta_data if isinstance(okta_data, list) else [okta_data]
        formatted_data = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping invalid record (not a dict): {item}")
                continue
            formatted_data.append({
                "review_id": item.get("id", ""),
                "campaign_id": item.get("campaignId", ""),
                "resource_id": item.get("resourceId", ""),
                "reviewer_id": item.get("reviewerId", ""),
                "reviewer_level": item.get("reviewerLevel", ""),
                "review_ids": item.get("reviewIds", []),
                "note": item.get("note", ""),
                "decision": item.get("decision", "UNASSIGNED"),
                "reviewer_type": item.get("reviewerType", ""),
                "current_reviewer_level": item.get("currentReviewerLevel", ""),
                "created": item.get("created", ""),
                "created_by": item.get("createdBy", ""),
                "last_updated": item.get("lastUpdated", ""),
                "last_updated_by": item.get("lastUpdatedBy", ""),
                "decided": item.get("decided", ""),
                "remediation_status": item.get("remediationStatus", ""),
                "principal_profile": item.get("principalProfile", {}),
            })
        logger.info("Extracted %d Review records", len(formatted_data))
        return formatted_data
