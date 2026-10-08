import numpy as np
import random

def generate_correlated_credit_score(income: float) -> int:
    """Generate a credit score somewhat correlated with income."""
    # Scale income roughly from 0.0 to 1.0 based on [20000, 500000] range
    normalized_income = min(max((income - 20000) / 480000, 0), 1)
    
    # Beta distribution, shifting right slightly with higher income
    a = 2 + (normalized_income * 3)
    b = 5 - (normalized_income * 2)
    
    # Scale to [300, 850]
    base = np.random.beta(a, b)
    score = 300 + (base * 550)
    return int(np.clip(score, 300, 850))

def accounts_per_customer(segment: str) -> int:
    """Poisson distribution with minimum 1 checking account."""
    if segment == "mass":
        lam = 1.0
    elif segment == "affluent":
        lam = 2.5
    elif segment == "hnw":
        lam = 4.0
    else:
        lam = 6.0
        
    return int(np.random.poisson(lam) + 1)

def txns_per_account_monthly(segment: str) -> int:
    """Poisson distribution for number of txns per month."""
    lambdas = {"mass": 15, "affluent": 25, "hnw": 40, "uhnw": 60}
    return int(np.random.poisson(lambdas.get(segment, 20)))

def txn_amount_distribution(segment: str) -> float:
    """Lognormal distribution of transaction amount per segment."""
    means = {"mass": 85, "affluent": 250, "hnw": 1200, "uhnw": 5000}
    mu = means.get(segment, 100)
    val = np.random.lognormal(mean=np.log(mu), sigma=1.0)
    return round(float(np.clip(val, 1, 100000)), 2)

def derive_risk_tolerance(age: int, segment: str) -> str:
    """Heuristic logic taking age and wealth into account."""
    score = 100
    # Older people are generally more conservative
    if age > 65:
        score -= 40
    elif age > 45:
        score -= 20
        
    # High net worth tends to have higher capacity for risk
    if segment in ["hnw", "uhnw"]:
        score += 30
        
    # Add random noise
    score += random.randint(-20, 20)
    
    if score < 40:
        return "conservative"
    elif score < 80:
        return "moderate"
    else:
        return "aggressive"
