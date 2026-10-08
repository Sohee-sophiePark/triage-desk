import numpy as np

def generate_income():
    """Lognormal distribution for income. Mean ~$65,000."""
    val = np.random.lognormal(mean=np.log(65000), sigma=0.8)
    return round(float(np.clip(val, 20000, 2000000)), 2)

def generate_age():
    """Normal distribution for age."""
    val = np.random.normal(loc=45, scale=12)
    return int(np.clip(val, 18, 90))

def determine_segment(income: float) -> str:
    """Determine client segment strictly based on income."""
    if income < 75000:
        return "mass"
    elif income < 250000:
        return "affluent"
    elif income < 1000000:
        return "hnw"
    else:
        return "uhnw"
