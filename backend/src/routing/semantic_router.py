"""
Semantic router for FinBot query classification.

Classifies incoming queries by intent before retrieval.
This makes retrieval more precise — instead of searching all
authorized collections, we target the most relevant one(s).

How it works:
    Each route has a name + a list of example utterances.
    At query time, the router computes cosine similarity between
    the query embedding and each route's utterance embeddings.
    The route with the highest similarity wins.

Routes defined:
    finance_route       → revenue, budgets, financial metrics
    engineering_route   → systems, incidents, architecture, SLA
    marketing_route     → campaigns, CAC, ROI, customer acquisition
    hr_general_route    → policies, leave, benefits, HR
    cross_department_route → broad queries spanning all collections
"""

import logging
from dataclasses import dataclass
from enum import Enum

import numpy as np
from fastembed import TextEmbedding

from src.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    FINANCE           = "finance_route"
    ENGINEERING       = "engineering_route"
    MARKETING         = "marketing_route"
    HR_GENERAL        = "hr_general_route"
    CROSS_DEPARTMENT  = "cross_department_route"


@dataclass
class RouteMatch:
    """Result of classifying a query."""
    route: RouteType          # Which route matched
    score: float              # Confidence score (0-1)
    target_collections: list[str]  # Collections to search


# ============================================================
# Route definitions
# Each route maps to target collections and has utterances
# that represent the kind of queries it handles.
# More utterances = better classification accuracy.
# These are grounded in your actual FinSolve documents.
# ============================================================
ROUTES: dict[RouteType, dict] = {

    RouteType.FINANCE: {
        "collections": ["finance", "general"],
        "utterances": [
            "What was our total revenue last year?",
            "Show me the budget variance for the technology department",
            "How much did we pay Amazon Web Services this year?",
            "What is our EBITDA margin for FY2024?",
            "Who are our top vendors by payment amount?",
            "What is FinSolve net income for 2024?",
            "How is our operating cash flow performing?",
            "What were the Q3 financial results?",
            "What is our vendor concentration risk?",
            "How much did we spend on cloud infrastructure?",
            "What are the finance department budget allocations?",
            "What is the gross profit margin this year?",
            "Show me the quarterly income statement",
            "What is the total operating expense for 2024?",
            "How did revenue grow compared to last year?",
        ],
    },

    RouteType.ENGINEERING: {
        "collections": ["engineering", "general"],
        "utterances": [
            "What happened during the payment gateway outage in February?",
            "What is our system architecture?",
            "Show me the incident log for 2024",
            "What is the SLA target for the payment service?",
            "How did our sprint velocity trend across the year?",
            "What was the root cause of the P0 data pipeline incident?",
            "How does FinSolve deploy to production?",
            "What database is used for transactional data?",
            "What was the test coverage percentage in Q4?",
            "What Kubernetes issue caused pod evictions?",
            "What is the API gateway latency target?",
            "How many incidents were P0 severity in 2024?",
            "What is the deployment success rate?",
            "How does the blue-green deployment work?",
            "What microservices does FinSolve use?",
        ],
    },

    RouteType.MARKETING: {
        "collections": ["marketing", "general"],
        "utterances": [
            "How many customers did we acquire in Q3?",
            "What was the ROI on our influencer campaigns?",
            "Which market had the best customer acquisition rate?",
            "What is our customer churn rate?",
            "How did the InstantPay launch campaign perform?",
            "What was our CAC last quarter?",
            "Show me social media engagement metrics",
            "How are Southeast Asia campaigns performing?",
            "What is the average customer lifetime value?",
            "Which campaigns should we scale in 2025?",
            "What was the Black Friday campaign revenue?",
            "How many new customers did we acquire in 2024?",
            "What was the marketing spend in Q2?",
            "How did the loyalty program perform?",
            "What is our brand awareness percentage?",
        ],
    },

    RouteType.HR_GENERAL: {
        "collections": ["general"],
        "utterances": [
            "How many days of annual leave do I get?",
            "What is the work from home policy?",
            "How do I apply for sick leave?",
            "What is the maternity leave entitlement?",
            "How do I file an IT support ticket?",
            "What is the notice period for a senior employee?",
            "Can I work from a different city?",
            "What gym subsidy does FinSolve offer?",
            "How does the annual performance review work?",
            "What is the employee referral bonus amount?",
            "What are the dress code requirements?",
            "What equipment is provided to junior engineers?",
            "How does the salary structure work?",
            "What is the code of conduct policy?",
            "How do I claim travel reimbursement?",
        ],
    },

    RouteType.CROSS_DEPARTMENT: {
        "collections": ["general", "finance", "engineering", "marketing"],
        "utterances": [
            "Give me an overview of how the company is doing",
            "What are the key highlights from 2024 across all departments?",
            "How has FinSolve grown as a company this year?",
            "What are our biggest achievements in 2024?",
            "Tell me about FinSolve Technologies as a company",
            "How many employees does FinSolve have?",
            "What markets does FinSolve operate in?",
            "What are FinSolve core products and services?",
            "Give me an executive briefing on company performance",
            "How is the company performing financially and operationally?",
            "What is FinSolve 2025 strategy?",
            "What products did FinSolve launch this year?",
        ],
    },
}


class SemanticRouter:
    """
    Classifies queries into routes using embedding similarity.

    On initialization, embeds all utterances for all routes.
    At query time, embeds the query and finds the closest route.
    """

    def __init__(self):
        self._model: TextEmbedding | None = None
        self._route_embeddings: dict[RouteType, np.ndarray] = {}
        self._initialized = False

    def _get_model(self) -> TextEmbedding:
        if self._model is None:
            logger.info(f"Loading router embedding model: {EMBEDDING_MODEL}")
            self._model = TextEmbedding(model_name=EMBEDDING_MODEL)
        return self._model

    def initialize(self) -> None:
        """
        Pre-compute embeddings for all route utterances.
        Call once at startup — not on every query.
        """
        if self._initialized:
            return

        logger.info("Initializing semantic router...")
        model = self._get_model()

        for route_type, route_config in ROUTES.items():
            utterances = route_config["utterances"]
            embeddings = list(model.embed(utterances))
            # Store mean embedding for the route
            # Mean of all utterance embeddings = centroid of the route
            self._route_embeddings[route_type] = np.mean(
                [e for e in embeddings], axis=0
            )
            logger.info(
                f"  Route '{route_type.value}': "
                f"{len(utterances)} utterances indexed"
            )

        self._initialized = True
        logger.info("✅ Semantic router initialized")

    def classify(self, query: str) -> RouteMatch:
        """
        Classify a query into a route.

        Args:
            query: The user's natural language question

        Returns:
            RouteMatch with the best matching route and score
        """
        if not self._initialized:
            self.initialize()

        model = self._get_model()

        # Embed the query
        query_embedding = np.array(list(model.embed([query]))[0])

        # Compute cosine similarity with each route centroid
        best_route = None
        best_score = -1.0

        for route_type, route_embedding in self._route_embeddings.items():
            # Cosine similarity
            score = float(
                np.dot(query_embedding, route_embedding) /
                (np.linalg.norm(query_embedding) * np.linalg.norm(route_embedding))
            )

            if score > best_score:
                best_score = score
                best_route = route_type

        target_collections = ROUTES[best_route]["collections"]

        logger.info(
            f"Route: '{best_route.value}' "
            f"(score={best_score:.3f}) "
            f"→ {target_collections}"
        )

        return RouteMatch(
            route=best_route,
            score=round(best_score, 4),
            target_collections=target_collections,
        )


# Module-level singleton — initialize once, reuse everywhere
_router: SemanticRouter | None = None


def get_router() -> SemanticRouter:
    """Returns the initialized router singleton."""
    global _router
    if _router is None:
        _router = SemanticRouter()
        _router.initialize()
    return _router


def classify_query(query: str) -> RouteMatch:
    """
    Convenience function — classify a query using the global router.

    Args:
        query: User's natural language question

    Returns:
        RouteMatch with route, score, and target collections
    """
    return get_router().classify(query)