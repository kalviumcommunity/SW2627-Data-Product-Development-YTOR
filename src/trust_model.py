from typing import Dict, Any, List
import pandas as pd
import numpy as np

def compute_seller_trust_score(
    total_orders: int,
    misleading_returns: int,
    late_orders: int,
    cancelled_orders: int,
    total_reviews: int,
    negative_reviews: int,
    avg_support_days: float,
    fake_review_flags: int = 0
) -> Dict[str, Any]:
    """
    Computes Seller Trust Score (0-100), individual penalties, and assigns a Risk Tier.
    """
    if total_orders == 0:
        return {
            "trust_score": 100.0,
            "risk_tier": "Low Risk",
            "misleading_return_rate": 0.0,
            "late_dispatch_rate": 0.0,
            "cancellation_rate": 0.0,
            "neg_sentiment_rate": 0.0,
            "penalties": {
                "misleading": 0.0,
                "late": 0.0,
                "cancellation": 0.0,
                "sentiment": 0.0,
                "support": 0.0,
                "fake_reviews": 0.0,
            }
        }
        
    misleading_rate = misleading_returns / max(1, total_orders)
    late_rate = late_orders / max(1, total_orders)
    cancel_rate = cancelled_orders / max(1, total_orders)
    neg_sentiment_rate = negative_reviews / max(1, total_reviews) if total_reviews > 0 else 0.0
    
    # Calculate weighted penalties
    p_misleading = min(30.0, misleading_rate * 250.0)
    p_late = min(25.0, late_rate * 120.0)
    p_cancel = min(25.0, cancel_rate * 200.0)
    p_sentiment = min(20.0, neg_sentiment_rate * 50.0)
    p_support = min(15.0, max(0.0, avg_support_days - 3.0) * 3.0)
    p_fake = min(15.0, fake_review_flags * 5.0)
    
    total_penalty = p_misleading + p_late + p_cancel + p_sentiment + p_support + p_fake
    raw_trust = 100.0 - total_penalty
    trust_score = float(np.clip(raw_trust, 0.0, 100.0))
    
    # Determine Risk Tier
    if trust_score < 50.0:
        risk_tier = "Critical Risk"
    elif trust_score < 70.0:
        risk_tier = "Moderate Risk"
    elif trust_score < 85.0:
        risk_tier = "Watchlist"
    else:
        risk_tier = "Low Risk"
        
    return {
        "trust_score": round(trust_score, 1),
        "risk_tier": risk_tier,
        "misleading_return_rate": round(misleading_rate * 100, 2),
        "late_dispatch_rate": round(late_rate * 100, 2),
        "cancellation_rate": round(cancel_rate * 100, 2),
        "neg_sentiment_rate": round(neg_sentiment_rate * 100, 2),
        "penalties": {
            "misleading": round(p_misleading, 1),
            "late": round(p_late, 1),
            "cancellation": round(p_cancel, 1),
            "sentiment": round(p_sentiment, 1),
            "support": round(p_support, 1),
            "fake_reviews": round(p_fake, 1),
        }
    }
