"""Generate the 3,000-row founder dataset (MASTER_PLAN step A5, user decision 2026-11-14).

Usage:
    python research/generate_dataset.py                # writes data/raw/full.jsonl
    python research/generate_dataset.py --out PATH --seed 42

Block 1 is the 50 real-grounded rows of data/raw/sample50.jsonl. Blocks 2-60 (2,950 rows) are
synthetic founders modelled on them: careers, education and prior startups are assembled from
pools of roles and generic employers, following the section 10 template and its consistency
rules. The user allowed made-up profiles for the full run ("fake based on real").

How outcomes are assigned: each synthetic profile gets a background score from its fields
(industry experience, prior exits, team, education, experience, a few interactions) plus
Gaussian noise. Within each block of 50 the noisy score is ranked and cut into exact counts
(25 shut down, 8 or 7 under $50M, 7 or 8 $50M-$500M, 5 $500M-$1B, 5 over $1B), so every block
has the target proportions, outcomes are only weakly predictable, and no single field is a
shortcut. Years are drawn per outcome band. Everything is seeded and reproducible.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import _industry_tokens, normalise  # noqa: E402  (same rules as the validator)

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTION = (
    "Based on this founder's profile at the time of founding, predict the company's "
    "outcome and how long it took."
)
SIZES = ["1-10", "11-50", "51-200", "201-1,000", "1,001-5,000", "5,000+"]
NOISE_SD = 0.62  # noise on the background score; tuned so outcomes stay hard to predict

# ---------------------------------------------------------------------------
# Employers: job industry label -> generic company nouns
# ---------------------------------------------------------------------------

EMPLOYERS = {
    "Internet": ["consumer internet company", "online classifieds company", "web portal company",
                 "online reviews website", "online search company"],
    "Software": ["software company", "business software company", "software consultancy",
                 "open-source software company", "mobile software company"],
    "SaaS": ["subscription software company", "customer relationship software company",
             "collaboration software company", "analytics software company",
             "marketing software company"],
    "Enterprise Software": ["enterprise software company", "database software company",
                            "IT management software company", "enterprise resource planning vendor"],
    "Cloud Computing": ["cloud hosting provider", "cloud infrastructure company", "web hosting company"],
    "Developer Tools": ["developer tools company", "code hosting company",
                        "software testing tools company", "application monitoring company"],
    "Data Infrastructure": ["database company", "data warehousing company", "data integration company"],
    "Data Analytics": ["analytics consultancy", "business intelligence company", "data analytics firm"],
    "Machine Learning Research": ["machine learning research lab", "artificial intelligence research lab"],
    "Cybersecurity": ["security software company", "network security company",
                      "security consulting firm", "identity management company"],
    "Networking Hardware": ["networking equipment maker", "telecom equipment maker"],
    "Semiconductors": ["semiconductor company", "chip design firm", "memory chip maker"],
    "Computer Hardware": ["computer hardware company", "data storage company", "server manufacturer"],
    "Consumer Electronics": ["consumer electronics company", "audio equipment maker", "camera maker",
                             "home appliance maker"],
    "Wearables": ["fitness tracker maker", "wearable device company"],
    "Robotics": ["robotics company", "warehouse automation company", "robotics research lab"],
    "Industrial Automation": ["industrial automation company", "factory equipment maker",
                              "industrial controls company"],
    "Drones and Aerial Imaging": ["drone maker", "aerial imaging company"],
    "Printing and Imaging": ["printer manufacturer", "3D printer maker", "imaging equipment company"],
    "Aerospace": ["aerospace manufacturer", "aircraft parts supplier", "aerospace contractor",
                  "satellite manufacturer"],
    "Space Systems": ["satellite operator", "launch services company", "space systems contractor"],
    "Defence": ["defence contractor", "national defence agency"],
    "Automotive": ["automotive manufacturer", "auto parts supplier", "car rental company",
                   "automotive engineering firm", "car dealership group"],
    "Electric Vehicles": ["electric vehicle maker", "electric vehicle charging company",
                          "battery pack supplier"],
    "Autonomous Vehicles": ["autonomous vehicle developer", "self-driving truck developer"],
    "Mobility Services": ["bike-sharing operator", "car-sharing company", "scooter-sharing company"],
    "Transportation": ["ride-hailing company", "public transit agency", "bus operator", "rail operator"],
    "Airlines": ["airline", "regional airline", "charter airline"],
    "Logistics": ["third-party logistics provider", "logistics company", "parcel carrier",
                  "warehousing company"],
    "Freight Transport": ["freight brokerage", "trucking company", "freight forwarder", "shipping line"],
    "Delivery Services": ["courier company", "same-day delivery company", "parcel delivery company"],
    "Supply Chain": ["supply chain consultancy", "contract logistics planner", "sourcing agent"],
    "Manufacturing": ["contract manufacturer", "industrial manufacturer", "electronics manufacturer",
                      "packaging manufacturer"],
    "Chemicals": ["chemical company", "specialty chemicals maker"],
    "Payments": ["payments processor", "card network", "point-of-sale payments company",
                 "money transfer company"],
    "Banking": ["retail bank", "commercial bank", "regional bank", "private bank"],
    "Investment Banking": ["investment bank", "boutique investment bank"],
    "Asset Management": ["asset management firm", "hedge fund", "mutual fund company"],
    "Wealth Management": ["wealth management firm", "financial advisory firm", "brokerage firm"],
    "Consumer Lending": ["consumer lender", "credit card issuer", "mortgage lender", "auto lender"],
    "Commercial Lending": ["commercial lender", "small business lender", "equipment finance company"],
    "Personal Finance": ["personal finance website", "budgeting app company", "credit monitoring company"],
    "Financial Services": ["financial services company", "financial data provider",
                           "stock exchange operator", "credit bureau"],
    "Insurance": ["insurance company", "insurance brokerage", "reinsurance company", "health insurer",
                  "auto insurer"],
    "Accounting": ["accounting firm", "audit firm", "tax preparation company"],
    "Venture Capital": ["venture capital firm", "seed fund", "corporate venture arm"],
    "Private Equity": ["private equity firm", "growth equity firm"],
    "Professional Services": ["management consulting firm", "strategy consultancy",
                              "professional services firm", "technology consultancy"],
    "Legal Services": ["corporate law firm", "litigation firm", "legal services provider"],
    "Government": ["national government agency", "city government office", "regulatory agency",
                   "national statistics office"],
    "Nonprofit": ["international development nonprofit", "education nonprofit", "health nonprofit",
                  "community foundation"],
    "Higher Education": ["public research university", "private university", "community college"],
    "Research": ["national research laboratory", "nonprofit research institute",
                 "government research lab"],
    "Health Care": ["hospital system", "university hospital", "community clinic",
                    "home health agency", "physician group"],
    "Primary Care": ["primary care practice", "urgent care chain"],
    "Mental Health Care": ["behavioural health clinic", "psychiatric hospital", "counselling practice"],
    "Senior Care": ["senior living operator", "home care agency", "nursing home operator"],
    "Clinical Research": ["clinical research organisation", "clinical trial site network"],
    "Pharmaceuticals": ["pharmaceutical company", "generic drug maker", "drug distributor"],
    "Biotech": ["biotech company", "gene therapy company", "antibody discovery company",
                "cell therapy company"],
    "Drug Development": ["drug development company", "drug discovery company",
                         "contract drug development lab"],
    "Medical Devices": ["medical device company", "surgical device maker", "orthopaedic implant maker",
                        "diagnostic imaging company"],
    "Diagnostics": ["diagnostics company", "clinical laboratory", "genetic testing company"],
    "Pharmacy": ["pharmacy chain", "independent pharmacy", "hospital pharmacy", "mail-order pharmacy"],
    "Telecommunications": ["mobile network operator", "telecommunications company", "cable operator",
                           "internet service provider"],
    "Media": ["newspaper publisher", "magazine publisher", "broadcast network", "news website",
              "media company"],
    "Digital Media": ["digital publisher", "online video network", "entertainment news website"],
    "Publishing": ["book publisher", "educational publisher", "magazine group"],
    "Video Production": ["video production company", "television production company", "film studio"],
    "Television": ["television network", "cable channel"],
    "Audio Production": ["radio station", "audio production company", "public radio network"],
    "Music": ["record label", "music streaming company", "concert promoter", "music publisher"],
    "Advertising": ["advertising agency", "ad network", "media buying agency",
                    "online advertising company"],
    "Marketing": ["marketing agency", "public relations firm", "market research firm",
                  "brand consultancy"],
    "Digital Marketing": ["digital marketing agency", "search marketing agency",
                          "email marketing company"],
    "Social Media": ["social networking company", "photo-sharing app company", "social media agency"],
    "Online Dating": ["online dating company", "dating app company"],
    "Mobile Apps": ["mobile app studio", "mobile app developer"],
    "Video Games": ["video game developer", "mobile game studio", "game publisher",
                    "console game developer"],
    "Gaming": ["online gaming company", "esports organisation", "casino gaming company"],
    "E-commerce": ["online retailer", "e-commerce company", "flash-sale website",
                   "online furniture retailer"],
    "Online Marketplaces": ["online marketplace", "peer-to-peer marketplace", "classifieds marketplace"],
    "Retail": ["department store chain", "grocery chain", "specialty retailer", "big-box retailer",
               "clothing retailer"],
    "Fashion": ["fashion brand", "apparel company", "luxury fashion house", "footwear brand"],
    "Beauty and Cosmetics": ["cosmetics company", "skincare brand", "beauty retailer"],
    "Consumer Goods": ["consumer goods company", "household products company", "personal care brand",
                       "packaged goods company"],
    "Food and Beverage": ["packaged food company", "beverage company", "snack food maker",
                          "dairy cooperative", "coffee roaster"],
    "Restaurant Operations": ["restaurant group", "fast-casual restaurant chain", "fine-dining restaurant",
                              "catering company"],
    "Food Delivery": ["food delivery company", "meal kit company"],
    "Hospitality": ["hotel chain", "boutique hotel", "resort operator", "hospitality management company"],
    "Travel": ["online travel agency", "travel agency", "tour operator", "cruise line"],
    "Event Management": ["event management company", "ticketing company", "conference organiser"],
    "Real Estate": ["real estate brokerage", "commercial real estate firm",
                    "real estate investment trust", "property developer"],
    "Property Management": ["property management company", "apartment operator",
                            "facilities management company"],
    "Construction": ["general contractor", "construction company", "engineering and construction firm",
                     "homebuilder"],
    "Architecture": ["architecture firm", "design and planning firm"],
    "Home Services": ["home improvement retailer", "home cleaning company", "plumbing services company",
                      "home renovation company"],
    "Home Security": ["home security company", "alarm monitoring company"],
    "Agriculture": ["agricultural equipment maker", "seed company", "crop protection company",
                    "farm cooperative", "grain trader"],
    "Commercial Farming": ["commercial farm", "greenhouse grower", "dairy farm"],
    "Renewable Energy": ["renewable energy developer", "wind energy company", "clean energy utility"],
    "Solar Energy": ["solar installer", "solar panel manufacturer", "solar project developer"],
    "Energy Storage": ["battery maker", "energy storage company"],
    "Utilities": ["electric utility", "gas utility"],
    "Oil and Gas": ["oil and gas company", "oilfield services company", "pipeline operator"],
    "Water Utilities": ["water utility", "water treatment company"],
    "Education": ["public school district", "charter school network", "private school",
                  "tutoring company", "test preparation company"],
    "Online Education": ["online learning company", "online course provider"],
    "Early Childhood Education": ["preschool operator", "early learning centre chain"],
    "Childcare": ["childcare centre", "nanny agency"],
    "Language Education": ["language school", "language tutoring company"],
    "Recruiting": ["recruiting agency", "executive search firm", "online job board"],
    "Staffing": ["staffing agency", "temporary staffing company"],
    "Payroll Services": ["payroll services company", "benefits administration company"],
    "Employee Benefits": ["benefits consultancy", "employee benefits provider"],
    "Human Resources": ["human resources consultancy", "HR outsourcing firm"],
    "Customer Support": ["customer support outsourcing firm", "call centre operator"],
    "Fitness": ["gym chain", "boutique fitness studio", "fitness equipment maker"],
    "Sports": ["professional sports team", "sports league", "sporting goods company",
               "sports media company"],
    "Pet Care": ["pet supplies retailer", "pet food company", "pet insurance company"],
    "Veterinary Care": ["veterinary clinic", "animal hospital"],
}

# Descriptions for very large employers (5,000+), by job industry.
BIG = {
    "Internet": ["a large search and advertising company", "a large web portal company",
                 "a large online travel company"],
    "Software": ["a large operating-system and productivity software company",
                 "a large business software company"],
    "Enterprise Software": ["a large enterprise software company", "a large database software company"],
    "E-commerce": ["a large online retailer", "a large online marketplace company"],
    "Social Media": ["a large social networking company"],
    "Consumer Electronics": ["a large consumer electronics and software company",
                             "a large consumer electronics maker"],
    "Cloud Computing": ["a large cloud computing provider"],
    "Payments": ["a large online payments company", "a large card network"],
    "Semiconductors": ["a large semiconductor company"],
    "Networking Hardware": ["a large networking equipment maker"],
    "Computer Hardware": ["a large computer hardware company"],
    "Transportation": ["a large ride-hailing company"],
    "Media": ["a large video streaming company", "a large broadcast network"],
    "SaaS": ["a large customer relationship software company"],
    "Telecommunications": ["a large mobile network operator"],
}

# How a founder's own earlier startup is described ("a seed-stage payments startup").
STARTUP_WORD = {"SaaS": "software-as-a-service", "E-commerce": "e-commerce", "Higher Education":
                "education", "Government": "government services", "Nonprofit": "social enterprise",
                "Research": "research", "Defence": "defence technology", "Utilities": "energy",
                "Investment Banking": "financial advisory", "Professional Services": "consulting",
                "Machine Learning Research": "machine learning", "Health Care": "health care",
                "Airlines": "aviation", "Television": "television production"}

# Employers that are institutions: plain size words only.
INSTITUTIONS = {"Government", "Higher Education", "Research", "Health Care", "Nonprofit",
                "Education", "Utilities", "Defence", "Water Utilities", "Primary Care",
                "Mental Health Care", "Senior Care", "Machine Learning Research"}
LARGE_LABELS = INSTITUTIONS | {"Banking", "Insurance", "Telecommunications", "Retail", "Automotive",
                               "Pharmaceuticals", "Airlines", "Oil and Gas", "Investment Banking",
                               "Consumer Goods", "Professional Services", "Aerospace", "Transportation"}
SMALL_LABELS = {"Venture Capital", "Private Equity", "Architecture", "Restaurant Operations",
                "Legal Services", "Veterinary Care", "Childcare", "Mobile Apps", "Home Services",
                "Marketing", "Digital Marketing", "Supply Chain", "Data Analytics",
                "Machine Learning Research"}
SIZE_W = {"default": [6, 14, 20, 21, 18, 21], "large": [1, 3, 8, 18, 30, 40],
          "small": [20, 35, 25, 12, 5, 3]}
MODS = {
    "1-10": ["small", "self-funded", "seed-stage", "boutique", "family-run"],
    "11-50": ["small", "early-stage", "venture-backed", "boutique", "family-owned"],
    "51-200": ["venture-backed", "growth-stage", "regional", "mid-sized", "privately held"],
    "201-1,000": ["mid-sized", "regional", "privately held", "venture-backed", "national"],
    "1,001-5,000": ["large", "national", "publicly listed", "established", "regional"],
    "5,000+": ["large", "global", "multinational", "large publicly listed", "national"],
}
NO_MOD_FIRST = {"national", "public", "private", "community", "city", "regional", "international",
                "government", "global", "local", "independent", "boutique", "professional"}
INST_MODS = {"1-10": ["small"], "11-50": ["small"], "51-200": ["small", "regional"],
             "201-1,000": ["regional", "mid-sized"], "1,001-5,000": ["large", "regional"],
             "5,000+": ["large", "national"]}

# ---------------------------------------------------------------------------
# Career tracks (role ladders by seniority 1-4) and the employers they work at
# ---------------------------------------------------------------------------

TRACKS = {
    "software": dict(kind="tech", roles={
        1: ["Software Engineer", "Junior Software Developer", "Web Developer", "Mobile Developer",
            "Associate Software Engineer", "Frontend Developer", "Backend Developer", "QA Engineer"],
        2: ["Software Engineer", "Senior Software Engineer", "Backend Engineer", "Full-Stack Engineer",
            "iOS Engineer", "Android Engineer", "Infrastructure Engineer", "Site Reliability Engineer",
            "Platform Engineer"],
        3: ["Senior Software Engineer", "Staff Software Engineer", "Tech Lead", "Engineering Manager",
            "Lead Developer", "Software Architect"],
        4: ["Principal Engineer", "Director of Engineering", "Vice President of Engineering",
            "Chief Technology Officer", "Head of Engineering"]},
        labels=["Internet", "Software", "SaaS", "Enterprise Software", "Cloud Computing",
                "Developer Tools", "Mobile Apps", "E-commerce", "Social Media", "Payments",
                "Video Games", "Telecommunications", "Financial Services", "Advertising", "Media"]),
    "hardware": dict(kind="tech", roles={
        1: ["Hardware Engineer", "Electrical Engineer", "Test Engineer", "Firmware Engineer"],
        2: ["Hardware Engineer", "Embedded Systems Engineer", "Firmware Engineer",
            "Product Design Engineer", "Electrical Engineer", "RF Engineer"],
        3: ["Senior Hardware Engineer", "Hardware Engineering Manager", "Lead Electrical Engineer",
            "Systems Architect"],
        4: ["Director of Hardware Engineering", "Vice President of Hardware", "Chief Technology Officer"]},
        labels=["Consumer Electronics", "Semiconductors", "Computer Hardware", "Networking Hardware",
                "Telecommunications", "Automotive", "Aerospace", "Wearables", "Manufacturing",
                "Medical Devices"]),
    "data": dict(kind="tech", roles={
        1: ["Data Analyst", "Business Intelligence Developer", "Quantitative Research Analyst",
            "Junior Data Scientist"],
        2: ["Data Scientist", "Data Engineer", "Machine Learning Engineer", "Quantitative Analyst",
            "Analytics Engineer"],
        3: ["Senior Data Scientist", "Lead Data Engineer", "Data Science Manager",
            "Senior Machine Learning Engineer"],
        4: ["Head of Data Science", "Director of Analytics", "Chief Data Officer",
            "Vice President of Data"]},
        labels=["Internet", "Data Analytics", "Financial Services", "Insurance", "Advertising",
                "E-commerce", "SaaS", "Asset Management", "Machine Learning Research",
                "Telecommunications", "Health Care"]),
    "science": dict(kind="tech", roles={
        1: ["Research Assistant", "Research Technician", "Graduate Researcher", "Research Associate"],
        2: ["Postdoctoral Researcher", "Research Scientist", "Scientist", "Staff Scientist"],
        3: ["Senior Scientist", "Principal Investigator", "Senior Research Scientist", "Group Leader"],
        4: ["Principal Scientist", "Director of Research", "Head of Research and Development",
            "Chief Scientific Officer"]},
        labels=["Higher Education", "Research", "Biotech", "Pharmaceuticals", "Chemicals",
                "Diagnostics", "Medical Devices", "Machine Learning Research", "Semiconductors"]),
    "robotics": dict(kind="tech", roles={
        1: ["Mechanical Engineer", "Robotics Engineer", "Controls Engineer", "Manufacturing Engineer"],
        2: ["Robotics Engineer", "Mechatronics Engineer", "Systems Engineer", "Perception Engineer",
            "Controls Engineer"],
        3: ["Senior Robotics Engineer", "Lead Systems Engineer", "Mechanical Engineering Manager",
            "Senior Mechanical Engineer"],
        4: ["Director of Robotics", "Head of Hardware Engineering", "Chief Technology Officer"]},
        labels=["Robotics", "Industrial Automation", "Automotive", "Aerospace", "Manufacturing",
                "Autonomous Vehicles", "Drones and Aerial Imaging", "Higher Education", "Defence",
                "Space Systems", "Electric Vehicles"]),
    "security": dict(kind="tech", roles={
        1: ["Security Analyst", "Network Administrator", "IT Support Engineer",
            "Security Operations Analyst"],
        2: ["Security Engineer", "Penetration Tester", "Security Consultant", "Incident Response Analyst"],
        3: ["Senior Security Engineer", "Security Architect", "Security Engineering Manager",
            "Principal Security Consultant"],
        4: ["Director of Security", "Chief Information Security Officer", "Vice President of Security"]},
        labels=["Cybersecurity", "Government", "Defence", "Banking", "Telecommunications",
                "Professional Services", "Internet", "Enterprise Software", "Financial Services"]),
    "consulting": dict(kind="biz", roles={
        1: ["Business Analyst", "Analyst", "Associate Consultant", "Research Associate"],
        2: ["Consultant", "Senior Consultant", "Associate", "Strategy Associate"],
        3: ["Engagement Manager", "Manager", "Principal"],
        4: ["Partner", "Associate Partner", "Director"]},
        labels=["Professional Services", "Accounting", "Supply Chain", "Human Resources"]),
    "finance": dict(kind="biz", roles={
        1: ["Investment Banking Analyst", "Financial Analyst", "Credit Analyst",
            "Equity Research Associate", "Analyst"],
        2: ["Associate", "Senior Financial Analyst", "Investment Associate", "Portfolio Analyst"],
        3: ["Vice President", "Portfolio Manager", "Principal", "Director of Finance"],
        4: ["Managing Director", "Partner", "Chief Financial Officer", "Head of Corporate Development"]},
        labels=["Investment Banking", "Banking", "Asset Management", "Private Equity", "Venture Capital",
                "Financial Services", "Wealth Management", "Consumer Lending", "Commercial Lending",
                "Insurance"]),
    "product": dict(kind="biz", roles={
        1: ["Associate Product Manager", "Product Analyst", "Business Analyst", "Program Coordinator"],
        2: ["Product Manager", "Program Manager", "Product Owner", "Project Manager"],
        3: ["Senior Product Manager", "Group Product Manager", "Director of Product", "Product Lead"],
        4: ["Vice President of Product", "Chief Product Officer", "General Manager", "Head of Product"]},
        labels=["Internet", "Software", "SaaS", "Enterprise Software", "E-commerce", "Online Marketplaces",
                "Mobile Apps", "Travel", "Media", "Payments", "Financial Services", "Telecommunications",
                "Social Media"]),
    "marketing": dict(kind="biz", roles={
        1: ["Marketing Coordinator", "Marketing Associate", "Social Media Coordinator",
            "Account Coordinator"],
        2: ["Marketing Manager", "Brand Manager", "Growth Marketing Manager", "Account Manager",
            "Content Strategist", "Product Marketing Manager"],
        3: ["Senior Brand Manager", "Director of Marketing", "Head of Growth", "Marketing Director"],
        4: ["Vice President of Marketing", "Chief Marketing Officer", "Global Brand Director"]},
        labels=["Consumer Goods", "Advertising", "Marketing", "Digital Marketing", "Retail",
                "E-commerce", "Food and Beverage", "Beauty and Cosmetics", "Fashion", "Media",
                "Internet", "Hospitality", "Travel"]),
    "sales": dict(kind="biz", roles={
        1: ["Sales Development Representative", "Account Executive", "Sales Associate",
            "Inside Sales Representative"],
        2: ["Account Executive", "Business Development Manager", "Partnerships Manager",
            "Account Manager", "Key Account Manager"],
        3: ["Sales Director", "Regional Sales Manager", "Head of Partnerships",
            "Director of Business Development"],
        4: ["Vice President of Sales", "Chief Revenue Officer", "Head of Sales", "General Manager"]},
        labels=["SaaS", "Enterprise Software", "Telecommunications", "Medical Devices", "Pharmaceuticals",
                "Advertising", "Logistics", "Insurance", "Consumer Goods", "Manufacturing",
                "Financial Services"]),
    "operations": dict(kind="biz", roles={
        1: ["Operations Associate", "Operations Analyst", "Logistics Coordinator", "Project Coordinator",
            "Assistant Store Manager"],
        2: ["Operations Manager", "Project Manager", "Store Manager", "Supply Chain Analyst",
            "Regional Operations Manager"],
        3: ["Director of Operations", "Regional Manager", "Head of Operations", "Country Manager"],
        4: ["Vice President of Operations", "Chief Operating Officer", "General Manager"]},
        labels=["Logistics", "Retail", "E-commerce", "Transportation", "Food Delivery", "Hospitality",
                "Restaurant Operations", "Manufacturing", "Online Marketplaces", "Delivery Services",
                "Freight Transport", "Mobility Services"]),
}
TECH_TRACKS = ["software", "hardware", "data", "science", "robotics", "security"]

# Domain specialists: role ladders, degrees (degree, field) and their usual employers.
DOMAINS = {
    "medicine": dict(roles={1: ["Resident Physician", "Medical Intern", "Clinical Research Fellow"],
                            2: ["Physician", "Emergency Physician", "Hospitalist", "Attending Physician",
                                "Psychiatrist"],
                            3: ["Senior Physician", "Clinical Director", "Department Chief"],
                            4: ["Medical Director", "Chief Medical Officer", "Chief of Medicine"]},
                     pro=[("MD", "Medicine")], ba=["Biology", "Chemistry", "Neuroscience", "Biochemistry"],
                     labels=["Health Care", "Primary Care", "Mental Health Care", "Clinical Research"]),
    "nursing": dict(roles={1: ["Registered Nurse", "Staff Nurse"],
                           2: ["Charge Nurse", "Nurse Practitioner", "Clinical Nurse Specialist"],
                           3: ["Nurse Manager", "Director of Nursing"], 4: ["Chief Nursing Officer"]},
                    pro=[("MSc", "Nursing")], ba=["Nursing"],
                    labels=["Health Care", "Senior Care", "Primary Care"]),
    "pharmacy": dict(roles={1: ["Pharmacy Intern", "Staff Pharmacist", "Pharmacy Technician"],
                            2: ["Pharmacist", "Clinical Pharmacist"],
                            3: ["Pharmacy Manager", "Pharmacy Operations Director"],
                            4: ["Director of Pharmacy Services"]},
                     pro=[("PharmD", "Pharmacy")], ba=["Chemistry", "Biology"],
                     labels=["Pharmacy", "Health Care", "Pharmaceuticals"]),
    "bioscience": dict(roles={1: ["Research Associate", "Graduate Researcher"],
                              2: ["Postdoctoral Fellow", "Scientist", "Clinical Scientist"],
                              3: ["Senior Scientist", "Associate Director of Research",
                                  "Principal Investigator"],
                              4: ["Vice President of Research", "Chief Scientific Officer",
                                  "Head of Discovery"]},
                       pro=[("PhD", f) for f in ["Molecular Biology", "Biochemistry", "Immunology",
                                                 "Neuroscience", "Bioengineering", "Chemistry",
                                                 "Genetics", "Pharmacology"]],
                       ba=["Biology", "Chemistry", "Biochemistry", "Bioengineering"],
                       labels=["Biotech", "Pharmaceuticals", "Drug Development", "Diagnostics",
                               "Medical Devices", "Higher Education", "Research", "Clinical Research"]),
    "law": dict(roles={1: ["Law Clerk", "Junior Associate", "Paralegal"],
                       2: ["Associate Attorney", "Litigation Associate", "Corporate Associate"],
                       3: ["Senior Associate", "Corporate Counsel", "Senior Counsel"],
                       4: ["Partner", "General Counsel", "Deputy General Counsel"]},
                pro=[("JD", "Law"), ("LLM", "Law")], ba=["Political Science", "History", "Philosophy",
                                                         "English"],
                labels=["Legal Services", "Government", "Financial Services"]),
    "teaching": dict(roles={1: ["Teacher", "Teaching Fellow", "Tutor", "Classroom Teacher"],
                            2: ["Lead Teacher", "Curriculum Developer", "Instructional Designer",
                                "Department Head"],
                            3: ["Assistant Principal", "Director of Curriculum", "Academic Director"],
                            4: ["Principal", "Head of School", "Superintendent"]},
                     pro=[("MEd", "Education"), ("MA", "Teaching")],
                     ba=["English", "History", "Mathematics", "Education", "Psychology"],
                     labels=["Education", "Online Education", "Early Childhood Education",
                             "Language Education", "Nonprofit", "Publishing"]),
    "realestate": dict(roles={1: ["Leasing Agent", "Real Estate Analyst", "Acquisitions Analyst"],
                              2: ["Real Estate Agent", "Property Manager", "Development Associate",
                                  "Acquisitions Associate"],
                              3: ["Senior Property Manager", "Development Manager", "Managing Broker"],
                              4: ["Principal", "Managing Director", "Head of Development"]},
                       pro=[("MSc", "Real Estate")], ba=["Economics", "Urban Studies", "Finance",
                                                         "Urban Planning"],
                       labels=["Real Estate", "Property Management", "Construction"]),
    "construction": dict(roles={1: ["Site Engineer", "Field Engineer", "Assistant Estimator"],
                                2: ["Project Engineer", "Estimator", "Construction Project Manager",
                                    "Site Manager"],
                                3: ["Senior Project Manager", "Construction Manager"],
                                4: ["Director of Construction", "Vice President of Construction"]},
                         pro=[("MSc", "Construction Management"), ("BArch", "Architecture")],
                         ba=["Civil Engineering", "Construction Management"],
                         labels=["Construction", "Architecture", "Real Estate", "Home Services"]),
    "agronomy": dict(roles={1: ["Field Technician", "Agronomy Intern", "Crop Consultant"],
                            2: ["Agronomist", "Farm Manager", "Crop Scientist", "Field Sales Agronomist"],
                            3: ["Senior Agronomist", "Regional Agronomy Manager", "Head Grower"],
                            4: ["Director of Agronomy", "Vice President of Farming Operations"]},
                     pro=[("MSc", "Agricultural Economics"), ("PhD", "Plant Science")],
                     ba=["Agronomy", "Animal Science", "Plant Science"],
                     labels=["Agriculture", "Commercial Farming", "Food and Beverage", "Chemicals"]),
    "culinary": dict(roles={1: ["Line Cook", "Pastry Cook", "Prep Cook"],
                            2: ["Sous Chef", "Chef de Partie", "Food Scientist", "Product Developer"],
                            3: ["Chef de Cuisine", "Executive Chef", "Restaurant General Manager"],
                            4: ["Culinary Director", "Director of Food and Beverage"]},
                     pro=[("MSc", "Food Science")], ba=["Culinary Arts", "Food Science",
                                                        "Hospitality Management"],
                     labels=["Restaurant Operations", "Food and Beverage", "Hospitality"]),
    "journalism": dict(roles={1: ["Reporter", "Editorial Assistant", "Production Assistant", "Researcher"],
                              2: ["Producer", "Editor", "Correspondent", "Video Producer"],
                              3: ["Senior Editor", "Senior Producer", "Managing Editor"],
                              4: ["Executive Producer", "Editor in Chief", "Head of Programming"]},
                       pro=[("MA", "Journalism")], ba=["Journalism", "Film Studies", "English",
                                                       "Communications"],
                       labels=["Media", "Digital Media", "Publishing", "Television", "Audio Production",
                               "Video Production"]),
    "insurance": dict(roles={1: ["Actuarial Analyst", "Underwriting Assistant", "Claims Adjuster"],
                             2: ["Underwriter", "Actuary", "Claims Manager", "Pricing Analyst"],
                             3: ["Senior Underwriter", "Head of Pricing", "Senior Actuary"],
                             4: ["Chief Actuary", "Chief Underwriting Officer"]},
                      pro=[("MSc", "Statistics")], ba=["Actuarial Science", "Mathematics", "Statistics"],
                      labels=["Insurance", "Financial Services"]),
    "markets": dict(roles={1: ["Junior Trader", "Credit Analyst", "Loan Officer"],
                           2: ["Trader", "Portfolio Analyst", "Risk Manager", "Relationship Manager"],
                           3: ["Portfolio Manager", "Head of Trading", "Senior Risk Manager"],
                           4: ["Chief Risk Officer", "Chief Investment Officer"]},
                    pro=[("MSc", "Financial Engineering"), ("MSc", "Finance")],
                    ba=["Finance", "Economics", "Mathematics"],
                    labels=["Banking", "Asset Management", "Wealth Management", "Consumer Lending",
                            "Commercial Lending", "Payments", "Financial Services", "Investment Banking"]),
    "logistics": dict(roles={1: ["Dispatcher", "Logistics Coordinator", "Warehouse Supervisor",
                                 "Freight Agent"],
                             2: ["Fleet Manager", "Supply Chain Planner", "Freight Broker",
                                 "Transportation Manager"],
                             3: ["Director of Logistics", "Regional Operations Director",
                                 "Head of Supply Chain"],
                             4: ["Vice President of Supply Chain", "Chief Operating Officer"]},
                      pro=[("MSc", "Supply Chain Management")],
                      ba=["Supply Chain Management", "Logistics", "Business Administration"],
                      labels=["Logistics", "Freight Transport", "Delivery Services", "Supply Chain",
                              "Retail", "Manufacturing"]),
    "energy": dict(roles={1: ["Energy Analyst", "Field Engineer", "Junior Project Developer"],
                          2: ["Project Developer", "Grid Engineer", "Energy Consultant", "Plant Engineer"],
                          3: ["Senior Project Manager", "Head of Project Development"],
                          4: ["Director of Development", "Vice President of Development"]},
                   pro=[("MSc", "Energy Systems"), ("PhD", "Materials Science")],
                   ba=["Electrical Engineering", "Environmental Science", "Chemical Engineering"],
                   labels=["Renewable Energy", "Solar Energy", "Utilities", "Energy Storage", "Oil and Gas",
                           "Water Utilities"]),
    "aviation": dict(roles={1: ["Flight Instructor", "Aerospace Engineer", "Flight Test Engineer"],
                            2: ["Commercial Pilot", "Propulsion Engineer", "Avionics Engineer"],
                            3: ["Senior Aerospace Engineer", "Chief Engineer", "Captain"],
                            4: ["Director of Flight Operations", "Vice President of Engineering"]},
                     pro=[("MSc", "Aeronautics")], ba=["Aerospace Engineering", "Aviation"],
                     labels=["Aerospace", "Airlines", "Space Systems", "Defence",
                             "Drones and Aerial Imaging"]),
    "fashion": dict(roles={1: ["Assistant Buyer", "Design Assistant", "Stylist", "Merchandising Assistant"],
                           2: ["Buyer", "Fashion Designer", "Merchandiser", "Product Developer"],
                           3: ["Senior Designer", "Merchandising Director", "Design Director"],
                           4: ["Creative Director", "Vice President of Merchandising"]},
                    pro=[("MA", "Fashion")], ba=["Fashion Design", "Textile Design",
                                                 "Fashion Merchandising"],
                    labels=["Fashion", "Retail", "Beauty and Cosmetics"]),
    "gamedev": dict(roles={1: ["Junior Game Designer", "Quality Assurance Tester", "Level Designer"],
                           2: ["Game Designer", "Game Producer", "Technical Artist"],
                           3: ["Lead Game Designer", "Senior Producer"],
                           4: ["Creative Director", "Studio Head", "Executive Producer"]},
                    pro=[("MFA", "Game Design")], ba=["Game Design", "Animation", "Computer Science"],
                    labels=["Video Games", "Gaming", "Mobile Apps"]),
    "recruiting": dict(roles={1: ["Recruiting Coordinator", "Recruiter", "HR Assistant"],
                              2: ["Senior Recruiter", "Talent Acquisition Partner", "HR Business Partner"],
                              3: ["Talent Acquisition Manager", "Head of Talent", "HR Director"],
                              4: ["Vice President of People", "Chief People Officer"]},
                       pro=[("MSc", "Human Resource Management")], ba=["Psychology", "Sociology",
                                                                       "Business Administration"],
                       labels=["Recruiting", "Staffing", "Human Resources", "Payroll Services"]),
    "hospitality": dict(roles={1: ["Front Desk Agent", "Travel Consultant", "Guest Services Associate"],
                               2: ["Front Office Manager", "Revenue Manager", "Hotel Sales Manager"],
                               3: ["Hotel General Manager", "Director of Revenue"],
                               4: ["Regional Vice President", "Vice President of Hotel Operations"]},
                        pro=[("MSc", "Hospitality Management")], ba=["Hospitality Management",
                                                                     "Tourism Management"],
                        labels=["Hospitality", "Travel", "Airlines", "Event Management"]),
    "fitness": dict(roles={1: ["Personal Trainer", "Fitness Instructor", "Athletic Trainer"],
                           2: ["Physical Therapist", "Strength and Conditioning Coach", "Studio Manager"],
                           3: ["Head Coach", "Director of Performance"],
                           4: ["Director of Sports Science"]},
                    pro=[("DPT", "Physical Therapy")], ba=["Kinesiology", "Sports Science"],
                    labels=["Fitness", "Sports", "Health Care"]),
    "veterinary": dict(roles={1: ["Veterinary Technician", "Associate Veterinarian"],
                              2: ["Veterinarian", "Relief Veterinarian"],
                              3: ["Lead Veterinarian", "Hospital Medical Director"],
                              4: ["Chief Veterinary Officer"]},
                       pro=[("DVM", "Veterinary Medicine")], ba=["Animal Science", "Biology"],
                       labels=["Veterinary Care", "Pet Care"]),
    "policy": dict(roles={1: ["Legislative Aide", "Policy Analyst", "Program Associate"],
                          2: ["Policy Advisor", "Program Manager", "Senior Policy Analyst"],
                          3: ["Deputy Director", "Chief of Staff"],
                          4: ["Agency Director", "Commissioner"]},
                   pro=[("MPP", "Public Policy"), ("MPA", "Public Administration")],
                   ba=["Political Science", "Economics", "Public Policy"],
                   labels=["Government", "Nonprofit", "Research"]),
    "music": dict(roles={1: ["Audio Engineer", "Production Assistant", "Music Programmer"],
                         2: ["Music Producer", "Artist Manager", "Label Manager"],
                         3: ["Head of Artist Relations", "Director of Programming"],
                         4: ["Label General Manager"]},
                  pro=[("MA", "Music Business")], ba=["Music", "Music Business", "Audio Engineering"],
                  labels=["Music", "Audio Production", "Event Management"]),
    "accounting": dict(roles={1: ["Staff Accountant", "Audit Associate", "Tax Associate"],
                              2: ["Senior Accountant", "Audit Senior", "Tax Manager"],
                              3: ["Controller", "Audit Manager"],
                              4: ["Chief Financial Officer", "Audit Partner"]},
                       pro=[("MSc", "Accountancy")], ba=["Accounting", "Finance"],
                       labels=["Accounting", "Professional Services", "Financial Services"]),
}

# ---------------------------------------------------------------------------
# Startup industries: weight, score effect, domain, technical track, related job
# industries (share a word with the name), adjacent ones, background mix
# (technical, business, mixed, domain specialist)
# ---------------------------------------------------------------------------

I = []


def ind(name, w, eff, dom, tech, rel, adj, bgw, biz=None):
    I.append(dict(name=name, w=w, eff=eff, dom=dom, tech=tech, rel=rel, adj=adj, bgw=bgw,
                  biz=biz or ["product", "sales", "consulting", "operations", "marketing", "finance"]))


FIN = ["finance", "product", "consulting", "sales"]
CON = ["marketing", "operations", "product", "consulting", "sales"]
B2B = ["sales", "product", "consulting", "finance"]
ind("payments", 3, .15, "markets", "software", ["Payments"], ["Banking", "Financial Services"], (35, 30, 25, 10), FIN)
ind("consumer lending", 2, .05, "markets", "data", ["Consumer Lending"], ["Banking", "Financial Services"], (25, 40, 20, 15), FIN)
ind("personal finance", 2, -.05, "markets", "software", ["Personal Finance"], ["Banking", "Wealth Management"], (30, 40, 20, 10), FIN)
ind("wealth management", 1.5, 0, "markets", "software", ["Wealth Management"], ["Asset Management", "Banking"], (20, 35, 20, 25), FIN)
ind("small business lending", 1.5, .05, "markets", "data", ["Commercial Lending"], ["Banking"], (20, 40, 20, 20), FIN)
ind("core banking technology", 1, .1, "markets", "software", ["Banking"], ["Financial Services"], (40, 25, 25, 10), FIN)
ind("insurance technology", 2, .1, "insurance", "data", ["Insurance"], ["Financial Services"], (30, 30, 20, 20), FIN)
ind("accounting automation", 1.5, .05, "accounting", "software", ["Accounting"], ["Professional Services"], (35, 30, 20, 15), FIN)
ind("primary care", 1.5, 0, "medicine", "software", ["Primary Care", "Health Care"], ["Insurance"], (15, 30, 15, 40))
ind("mental health", 1.5, -.05, "medicine", "software", ["Mental Health Care", "Health Care"], ["Insurance"], (20, 30, 15, 35))
ind("senior care", 1, -.05, "nursing", "software", ["Senior Care", "Health Care"], ["Insurance"], (15, 35, 15, 35), CON)
ind("clinical trials", 1, .1, "bioscience", "data", ["Clinical Research"], ["Pharmaceuticals", "Biotech"], (25, 25, 15, 35), B2B)
ind("biotech", 3, .25, "bioscience", "science", ["Biotech"], ["Pharmaceuticals", "Higher Education"], (30, 10, 10, 50), ["finance", "consulting", "sales"])
ind("drug discovery", 1.5, .2, "bioscience", "science", ["Drug Development"], ["Biotech", "Pharmaceuticals"], (35, 5, 10, 50), ["finance", "consulting"])
ind("medical devices", 2, .1, "bioscience", "hardware", ["Medical Devices"], ["Health Care"], (40, 15, 15, 30), B2B)
ind("diagnostics", 1.5, .05, "bioscience", "science", ["Diagnostics"], ["Biotech", "Health Care"], (30, 15, 15, 40), B2B)
ind("online pharmacy", 1, 0, "pharmacy", "software", ["Pharmacy"], ["Health Care", "E-commerce"], (20, 30, 15, 35), CON)
ind("B2B SaaS", 4, .2, None, "software", ["SaaS"], ["Enterprise Software", "Software"], (45, 30, 25, 0), B2B)
ind("developer tools", 3, .15, None, "software", ["Developer Tools"], ["Software", "Cloud Computing"], (75, 5, 20, 0), B2B)
ind("cybersecurity", 3, .2, None, "security", ["Cybersecurity"], ["Defence", "Government"], (65, 10, 25, 0), B2B)
ind("data infrastructure", 2, .2, None, "data", ["Data Infrastructure", "Data Analytics"], ["Cloud Computing"], (70, 5, 25, 0), B2B)
ind("cloud infrastructure", 2, .15, None, "software", ["Cloud Computing"], ["Enterprise Software"], (70, 5, 25, 0), B2B)
ind("machine learning platforms", 2, .1, None, "data", ["Machine Learning Research"], ["Data Analytics", "Internet"], (70, 5, 25, 0), B2B)
ind("customer support automation", 1, .05, None, "software", ["Customer Support"], ["SaaS"], (40, 30, 30, 0), B2B)
ind("marketing technology", 2, .05, None, "software", ["Marketing", "Digital Marketing"], ["Advertising"], (35, 35, 30, 0), ["marketing", "sales", "product"])
ind("advertising technology", 2, 0, None, "data", ["Advertising"], ["Digital Marketing", "Media"], (40, 30, 30, 0), ["marketing", "sales", "product"])
ind("legal technology", 1, 0, "law", "software", ["Legal Services"], ["Professional Services"], (30, 20, 15, 35), B2B)
ind("government technology", 1, 0, "policy", "software", ["Government"], ["Nonprofit", "Research"], (35, 25, 20, 20), B2B)
ind("telecommunications", 1, 0, None, "hardware", ["Telecommunications"], ["Networking Hardware"], (50, 30, 20, 0), B2B)
ind("supply chain analytics", 1.5, .05, "logistics", "data", ["Supply Chain"], ["Logistics", "Manufacturing"], (35, 30, 20, 15), B2B)
ind("e-commerce", 3, -.05, None, "software", ["E-commerce"], ["Retail"], (25, 50, 25, 0), CON)
ind("online marketplaces", 3, 0, None, "software", ["Online Marketplaces"], ["E-commerce", "Internet"], (30, 45, 25, 0), CON)
ind("fashion e-commerce", 1.5, -.15, "fashion", "software", ["Fashion", "E-commerce"], ["Retail"], (10, 45, 15, 30), CON)
ind("beauty products", 1.5, -.05, "fashion", None, ["Beauty and Cosmetics"], ["Consumer Goods", "Retail"], (0, 65, 10, 25), CON)
ind("consumer goods", 2, -.05, None, None, ["Consumer Goods"], ["Retail", "Food and Beverage"], (0, 75, 25, 0), CON)
ind("retail technology", 1.5, 0, None, "software", ["Retail"], ["E-commerce"], (35, 35, 30, 0), CON)
ind("food and beverage", 2, -.05, "culinary", None, ["Food and Beverage"], ["Consumer Goods", "Restaurant Operations"], (0, 55, 15, 30), CON)
ind("food delivery", 2, -.2, None, "software", ["Food Delivery", "Delivery Services"], ["Restaurant Operations"], (30, 50, 20, 0), CON)
ind("restaurant technology", 1, -.05, "culinary", "software", ["Restaurant Operations"], ["Hospitality"], (35, 30, 15, 20), CON)
ind("automotive retail", 1, -.05, None, "software", ["Automotive"], ["Online Marketplaces"], (20, 55, 25, 0), CON)
ind("logistics", 2, .05, "logistics", "software", ["Logistics"], ["Freight Transport", "Supply Chain"], (25, 30, 20, 25), B2B + ["operations"])
ind("freight brokerage", 1, 0, "logistics", "software", ["Freight Transport"], ["Logistics"], (20, 35, 20, 25), B2B + ["operations"])
ind("last-mile delivery", 1.5, -.15, "logistics", "software", ["Delivery Services"], ["Logistics", "Food Delivery"], (25, 40, 20, 15), CON)
ind("urban mobility", 1.5, -.15, None, "robotics", ["Mobility Services"], ["Transportation", "Automotive"], (40, 35, 25, 0), CON)
ind("electric vehicles", 1, -.1, None, "robotics", ["Electric Vehicles"], ["Automotive"], (55, 20, 25, 0), B2B)
ind("autonomous vehicles", 1, 0, None, "robotics", ["Autonomous Vehicles"], ["Automotive", "Robotics"], (80, 5, 15, 0), B2B)
ind("solar energy", 1.5, -.05, "energy", "hardware", ["Solar Energy", "Renewable Energy"], ["Utilities"], (30, 30, 15, 25), B2B)
ind("energy storage", 1, 0, "energy", "science", ["Energy Storage", "Renewable Energy"], ["Automotive", "Utilities"], (50, 10, 15, 25), B2B)
ind("water technology", .7, -.05, "energy", "science", ["Water Utilities"], ["Utilities"], (40, 20, 15, 25), B2B)
ind("agriculture technology", 1.5, 0, "agronomy", "robotics", ["Agriculture"], ["Food and Beverage"], (35, 20, 15, 30), B2B)
ind("indoor farming", .8, -.15, "agronomy", "robotics", ["Commercial Farming"], ["Agriculture"], (25, 35, 15, 25), CON)
ind("online education", 2.5, -.05, "teaching", "software", ["Education", "Online Education"], ["Publishing", "Higher Education"], (25, 35, 15, 25), CON)
ind("language learning", 1, 0, "teaching", "software", ["Language Education"], ["Education"], (30, 35, 15, 20), CON)
ind("early childhood education", .8, -.1, "teaching", None, ["Early Childhood Education", "Education"], ["Childcare"], (0, 50, 10, 40), CON)
ind("recruiting", 1.5, 0, "recruiting", "software", ["Recruiting"], ["Staffing", "Human Resources"], (30, 40, 15, 15), B2B)
ind("staffing marketplaces", 1, -.05, "recruiting", "software", ["Staffing"], ["Recruiting"], (25, 45, 15, 15), B2B)
ind("payroll and benefits", 1, .1, "recruiting", "software", ["Payroll Services", "Employee Benefits"], ["Human Resources", "Insurance"], (35, 35, 20, 10), B2B)
ind("real estate technology", 2, 0, "realestate", "software", ["Real Estate"], ["Property Management", "Construction"], (25, 40, 15, 20), CON)
ind("property management", 1, -.05, "realestate", "software", ["Property Management"], ["Real Estate"], (20, 40, 15, 25), CON)
ind("construction technology", 1, .05, "construction", "software", ["Construction"], ["Architecture", "Real Estate"], (30, 20, 15, 35), B2B)
ind("home services", 1.5, -.15, None, "software", ["Home Services"], ["Retail"], (20, 55, 25, 0), CON)
ind("travel", 2, -.05, "hospitality", "software", ["Travel"], ["Hospitality", "Airlines"], (30, 40, 15, 15), CON)
ind("hospitality", 1, -.05, "hospitality", "software", ["Hospitality"], ["Travel", "Event Management"], (20, 40, 15, 25), CON)
ind("event ticketing", .8, -.1, "music", "software", ["Event Management"], ["Music", "Sports"], (30, 40, 15, 15), CON)
ind("mobile games", 2, -.05, "gamedev", "software", ["Video Games"], ["Mobile Apps"], (45, 15, 15, 25), CON)
ind("esports", .7, -.15, "gamedev", "software", ["Gaming"], ["Video Games", "Sports"], (30, 35, 15, 20), CON)
ind("digital media", 2, -.15, "journalism", "software", ["Media", "Digital Media"], ["Publishing", "Advertising"], (15, 40, 15, 30), CON)
ind("audio content", 1, -.05, "journalism", "software", ["Audio Production"], ["Media", "Music"], (20, 35, 15, 30), CON)
ind("music streaming", 1, -.1, "music", "software", ["Music"], ["Media"], (35, 30, 15, 20), CON)
ind("video streaming", 1, -.05, "journalism", "software", ["Video Production"], ["Media", "Television"], (35, 30, 15, 20), CON)
ind("social media", 2.5, -.2, None, "software", ["Social Media"], ["Internet", "Mobile Apps"], (45, 30, 25, 0), CON)
ind("online dating", 1, -.1, None, "software", ["Online Dating"], ["Social Media", "Internet"], (35, 35, 30, 0), CON)
ind("fitness", 1.5, -.1, "fitness", "software", ["Fitness"], ["Health Care", "Sports"], (20, 35, 15, 30), CON)
ind("sports technology", 1, -.05, "fitness", "data", ["Sports"], ["Fitness", "Media"], (35, 30, 15, 20), CON)
ind("pet care", 1, -.05, "veterinary", "software", ["Pet Care", "Veterinary Care"], ["Retail"], (15, 45, 15, 25), CON)
ind("consumer electronics", 2, -.2, None, "hardware", ["Consumer Electronics"], ["Wearables", "Manufacturing"], (55, 15, 30, 0), CON)
ind("consumer robotics", 1, -.2, None, "robotics", ["Robotics"], ["Consumer Electronics"], (70, 5, 25, 0), CON)
ind("industrial robotics", 1, .05, None, "robotics", ["Robotics", "Industrial Automation"], ["Manufacturing"], (70, 10, 20, 0), B2B)
ind("drones", 1, -.1, "aviation", "robotics", ["Drones and Aerial Imaging"], ["Aerospace"], (60, 10, 20, 10), B2B)
ind("semiconductors", 1, .15, None, "hardware", ["Semiconductors"], ["Computer Hardware"], (80, 5, 15, 0), B2B)
ind("3D printing", .8, -.05, None, "hardware", ["Printing and Imaging"], ["Manufacturing"], (60, 15, 25, 0), B2B)
ind("wearables", 1, -.15, None, "hardware", ["Wearables"], ["Consumer Electronics", "Fitness"], (55, 15, 30, 0), CON)
ind("space technology", .7, .05, "aviation", "robotics", ["Space Systems"], ["Aerospace", "Defence"], (70, 5, 10, 15), B2B)
ind("home security", .7, -.05, None, "hardware", ["Home Security"], ["Consumer Electronics"], (45, 30, 25, 0), CON)

DEEP_TECH = {"biotech", "drug discovery", "medical devices", "diagnostics", "semiconductors",
             "cybersecurity", "data infrastructure", "machine learning platforms", "energy storage",
             "autonomous vehicles", "industrial robotics", "space technology", "developer tools",
             "cloud infrastructure"}
SPECIALIST_DOMAINS = {"bioscience", "medicine", "pharmacy", "law", "insurance", "nursing", "markets"}

TECH_FIELDS = ["Computer Science", "Electrical Engineering", "Mechanical Engineering",
               "Computer Engineering", "Physics", "Mathematics", "Statistics", "Chemical Engineering",
               "Aerospace Engineering", "Bioengineering", "Materials Science", "Information Systems",
               "Industrial Engineering", "Civil Engineering", "Applied Mathematics",
               "Software Engineering", "Electrical and Computer Engineering", "Operations Research"]
TRACK_FIELDS = {"software": ["Computer Science", "Software Engineering", "Computer Engineering",
                             "Mathematics", "Information Systems"],
                "hardware": ["Electrical Engineering", "Computer Engineering",
                             "Electrical and Computer Engineering", "Physics"],
                "data": ["Statistics", "Mathematics", "Computer Science", "Applied Mathematics",
                         "Operations Research", "Physics"],
                "science": ["Chemistry", "Biology", "Physics", "Materials Science", "Chemical Engineering",
                            "Bioengineering"],
                "robotics": ["Mechanical Engineering", "Aerospace Engineering", "Electrical Engineering",
                             "Mechatronics", "Robotics"],
                "security": ["Computer Science", "Information Systems", "Computer Engineering",
                             "Mathematics"]}
PHD_FIELDS = {"software": ["Computer Science"], "hardware": ["Electrical Engineering"],
              "data": ["Statistics", "Computer Science", "Machine Learning"],
              "science": ["Chemistry", "Physics", "Materials Science", "Biochemistry"],
              "robotics": ["Robotics", "Mechanical Engineering", "Aerospace Engineering"],
              "security": ["Computer Science"]}
BIZ_FIELDS = ["Economics", "Business Administration", "Finance", "Accounting", "Marketing",
              "Political Science", "History", "English", "Psychology", "International Relations",
              "Communications", "Philosophy", "Sociology", "Government", "Management",
              "International Business", "Mathematics", "Geography", "Anthropology"]
BIZ_DEGREE = ["BA", "BA", "BSc", "BBA", "BCom"]
QS_W = {"under": [20, 14, 28, 22, 16], "grad": [33, 17, 27, 13, 10]}
QS = ["top 50", "51-100", "101-300", "300+", "unranked"]
YEARS_W = {"shut down": [56, 34, 10], "under $50M": [55, 36, 9], "$50M-$500M": [30, 46, 24],
           "$500M-$1B": [24, 50, 26], "over $1B": [7, 53, 40]}
YEARS = ["under 5", "5-8", "over 8"]


# ---------------------------------------------------------------------------
# Building one profile
# ---------------------------------------------------------------------------


def article(word: str) -> str:
    return "an" if word[0].lower() in "aeiou" else "a"


def bucket_dur(y: float) -> str:
    return "<1" if y < 1 else "1-2" if y < 2 else "2-3" if y < 3 else "3-5" if y < 5 else "5+"


def bucket_exp(y: float) -> str:
    return "<5" if y < 5 else "5-10" if y < 10 else "10-15" if y < 15 else "15+"


def level(cum: float) -> int:
    return 1 if cum < 2.5 else 2 if cum < 6.5 else 3 if cum < 12 else 4


def pick(rng, xs, w=None):
    return rng.choices(xs, weights=w)[0] if w else rng.choice(xs)


def company(rng, label: str, size: str) -> str:
    if size == "5,000+" and label in BIG and rng.random() < 0.55:
        return pick(rng, BIG[label])
    noun = pick(rng, EMPLOYERS[label])
    mods = INST_MODS if label in INSTITUTIONS else MODS
    if noun.split()[0] in NO_MOD_FIRST or (rng.random() < 0.3 and label not in INSTITUTIONS):
        return f"{article(noun)} {noun}"
    mod = pick(rng, mods[size])
    return f"{article(mod)} {mod} {noun}"


def size_for(rng, label: str, startup: bool = False) -> str:
    if startup:
        return pick(rng, SIZES[:3], [35, 45, 20])
    key = "large" if label in LARGE_LABELS else "small" if label in SMALL_LABELS else "default"
    return pick(rng, SIZES, SIZE_W[key])


def overlaps(ind_name: str, label: str, comp: str) -> bool:
    return bool(_industry_tokens(ind_name) & _industry_tokens(label + " " + comp))


def make_edu(rng, bg, it, track):
    """List of (degree, field or None, qs)."""
    edu = []
    r = rng.random()
    dom = DOMAINS.get(it["dom"]) if bg == "domain specialist" else None
    if bg in ("technical", "business", "mixed") and r < 0.075:
        if r < 0.018:
            return [("no degree", None, None)]
        field = pick(rng, TRACK_FIELDS[track]) if bg != "business" else pick(rng, BIZ_FIELDS)
        return [("no degree", field, pick(rng, QS, QS_W["under"]))]
    if bg == "technical":
        f = pick(rng, TRACK_FIELDS[track] + TECH_FIELDS[:6])
        edu.append((pick(rng, ["BSc", "BSc", "BSc", "BEng"]), f, None))
        p = rng.random()
        phd_p = 0.32 if track in ("science", "robotics") or it["name"] in DEEP_TECH else 0.1
        if p < phd_p:
            if rng.random() < 0.5:
                edu.append(("MSc", f, None))
            edu.append(("PhD", pick(rng, PHD_FIELDS[track]), None))
        elif p < phd_p + 0.3:
            edu.append(("MSc", pick(rng, [f] + TRACK_FIELDS[track]), None))
        elif p < phd_p + 0.36:
            edu.append(("MBA", "Business Administration", None))
    elif bg == "business":
        f = pick(rng, BIZ_FIELDS)
        edu.append((pick(rng, BIZ_DEGREE) if f not in ("Mathematics",) else "BSc", f, None))
        p = rng.random()
        if p < 0.3:
            edu.append(("MBA", "Business Administration", None))
        elif p < 0.38:
            edu.append(("MSc", pick(rng, ["Finance", "Management", "Marketing", "Economics",
                                          "Accounting"]), None))
        elif p < 0.42:
            edu.append(("JD", "Law", None))
    elif bg == "mixed":
        if rng.random() < 0.75:
            f = pick(rng, TRACK_FIELDS[track] + TECH_FIELDS[:6])
            edu.append((pick(rng, ["BSc", "BEng"]), f, None))
        else:
            edu.append((pick(rng, BIZ_DEGREE), pick(rng, BIZ_FIELDS), None))
        p = rng.random()
        if p < 0.45:
            edu.append(("MBA", "Business Administration", None))
        elif p < 0.6:
            edu.append(("MSc", pick(rng, ["Management Science", "Engineering Management",
                                          "Computer Science", "Technology Management"]), None))
    else:  # domain specialist
        f = pick(rng, dom["ba"])
        deg = "BSc" if f not in ("English", "History", "Philosophy", "Political Science",
                                 "Journalism", "Film Studies", "Communications", "Music",
                                 "Fashion Design", "Textile Design", "Culinary Arts",
                                 "Urban Studies", "Sociology", "Psychology", "Education",
                                 "Animation", "Game Design", "Music Business") else "BA"
        edu.append((deg, f, None))
        pro_p = 0.9 if it["dom"] in ("medicine", "pharmacy", "law", "veterinary", "bioscience") else 0.35
        if rng.random() < pro_p:
            d, fld = pick(rng, dom["pro"])
            edu.append((d, fld, None))
            if it["dom"] == "medicine" and rng.random() < 0.15:
                edu.append(("MBA", "Business Administration", None))
        elif rng.random() < 0.25:
            edu.append(("MBA", "Business Administration", None))
    out = []
    for i, (d, f, _) in enumerate(edu[:3]):
        out.append((d, f, pick(rng, QS, QS_W["under" if i == 0 else "grad"])))
    return out


def prior_startups(rng, exp_bucket):
    p = {"<5": 0.08, "5-10": 0.25, "10-15": 0.38, "15+": 0.48}[exp_bucket]
    if rng.random() >= p:
        return []
    n = pick(rng, [1, 2, 3], [76, 20, 4])
    outs = []
    for _ in range(n):
        outs.append(pick(rng, ["shut down", "under $50M", "$50M-$500M", "operating", "$500M-$1B",
                               "over $1B"], [46, 30, 11, 9, 2.5, 1.5]))
    big = [o for o in outs if o in ("$500M-$1B", "over $1B")]
    if big and len(outs) > 1:  # keep large exits to single-startup founders (simpler text)
        outs = [o if o not in ("$500M-$1B", "over $1B") else "$50M-$500M" for o in outs]
    return outs


def startups_text(outs):
    if not outs:
        return "none", "none"
    parts = []
    n_shut = outs.count("shut down")
    if n_shut:
        parts.append(f"{n_shut} shut down")
    n_op = outs.count("operating")
    if n_op:
        parts.append(f"{n_op} still operating")
    exits = [o for o in outs if o not in ("shut down", "operating")]
    order = ["under $50M", "$50M-$500M", "$500M-$1B", "over $1B"]
    exits.sort(key=order.index)
    for o in exits:
        parts.append("1 IPO over $1B" if o == "over $1B" else f"1 acquired {o}")
    st = f"{len(outs)} founded before, " + ", ".join(parts)
    if not exits:
        return st, "none"
    if exits == ["over $1B"]:
        return st, "1 IPO as co-founder, over $1B"
    bands = []
    for o in exits:
        if o not in bands:
            bands.append(o)
    noun = "acquisition" if len(exits) == 1 else "acquisitions"
    return st, f"{len(exits)} {noun} as co-founder, " + " and ".join(bands)


def make_jobs(rng, it, bg, track, years, indexp, founder_jobs):
    """Jobs as (role, company, size, label, dur_years); also returns whether it worked."""
    k = max(1, min(6, round(years / rng.uniform(2.2, 4.8))))
    if years < 1.5:
        k = 1
    k = max(k, min(6, founder_jobs + 1)) if founder_jobs else k
    cuts = sorted(rng.uniform(0, 1) for _ in range(k - 1))
    shares = [b - a for a, b in zip([0] + cuts, cuts + [1])]
    shares = [max(s, 0.08) for s in shares]
    tot = sum(shares)
    durs = [years * s / tot for s in shares]
    # Which jobs are relevant to the startup's industry.
    rel_idx: set[int] = set()
    adj_idx: set[int] = set()
    if indexp == "deep":
        longest = max(range(k), key=lambda i: durs[i])
        rel_idx.add(longest if rng.random() < 0.5 else k - 1)
        if durs[max(rel_idx)] < 2.5:
            rel_idx.add(longest)
        for i in range(k):
            if rng.random() < 0.3:
                rel_idx.add(i)
    elif indexp == "some":
        i = pick(rng, range(k))
        if durs[i] < 3 and rng.random() < 0.6:
            rel_idx.add(i)
        else:
            adj_idx.add(i)
    dom = DOMAINS.get(it["dom"])
    fidx = set()
    if founder_jobs:
        cand = [i for i in range(k) if i > 0] or [0]
        fidx = set(rng.sample(cand, min(founder_jobs, len(cand))))
    biz_tracks = it["biz"]
    jobs, cum, prev_lv = [], 0.0, 1
    for i, d in enumerate(durs):
        lv = min(4, max(prev_lv, level(cum + d / 2) + pick(rng, [-1, 0, 0, 0])))
        prev_lv = lv
        cum += d
        # Role family for this job.
        if bg == "technical":
            fam = ("track", track)
        elif bg == "business":
            fam = ("track", pick(rng, biz_tracks))
        elif bg == "mixed":
            fam = ("track", track) if i < math.ceil(k / 2) and k > 1 or (k == 1 and rng.random() < .5) \
                else ("track", pick(rng, ["product", "product", "sales", "consulting", "operations"]))
        else:
            fam = ("domain", it["dom"]) if rng.random() < 0.85 or i in rel_idx else \
                ("track", pick(rng, ["consulting", "product", "operations"]))
        # Employer industry label.
        if i in rel_idx:
            label = pick(rng, it["rel"])
        elif i in adj_idx and it["adj"]:
            label = pick(rng, it["adj"])
        else:
            pool = DOMAINS[fam[1]]["labels"] if fam[0] == "domain" else TRACKS[fam[1]]["labels"]
            pool = [lb for lb in pool if lb not in it["rel"] and lb not in it["adj"]
                    and not overlaps(it["name"], lb, "")]
            if not pool:
                pool = [lb for lb in TRACKS["consulting"]["labels"] if not overlaps(it["name"], lb, "")]
            label = pick(rng, pool)
        if i in fidx:
            tech_founder = bg in ("technical",) or (bg == "mixed" and fam[1] in TECH_TRACKS)
            role = pick(rng, ["Co-founder and Chief Technology Officer", "Co-founder", "Founder"]
                        if tech_founder else
                        ["Co-founder and Chief Executive", "Founder and Chief Executive", "Co-founder",
                         "Founder"])
            size = size_for(rng, label, startup=True)
            mod = pick(rng, ["small", "early-stage", "seed-stage", "venture-backed", ""])
            sector = STARTUP_WORD.get(label, label.lower())
            comp = f"{article(mod or sector)} {(mod + ' ') if mod else ''}{sector} startup"
        else:
            roles = (DOMAINS[fam[1]]["roles"] if fam[0] == "domain" else TRACKS[fam[1]]["roles"])
            role = pick(rng, roles[lv])
            size = size_for(rng, label)
            comp = company(rng, label, size)
        jobs.append([role, comp, size, label, d])
    return jobs, rel_idx


def check_indexp(it, jobs, indexp) -> bool:
    ov = [overlaps(it["name"], lb, comp) for _, comp, _, lb, _ in jobs]
    if indexp == "none":
        return not any(ov)
    if indexp == "deep":
        return any(ov) and sum(d for (_, _, _, _, d), o in zip(jobs, ov) if o) >= 2.0
    return True


def background_score(p) -> float:
    """Deterministic part of the latent outcome score (higher = better odds)."""
    it, bg = p["it"], p["bg"]
    s = it["eff"]
    s += {"<5": -0.08, "5-10": 0.03, "10-15": 0.08, "15+": 0.05}[p["exp"]]
    s += {"deep": 0.32, "some": 0.12, "none": 0.0}[p["indexp"]]
    s += {"technical": 0.1, "business": 0.0, "mixed": 0.12, "domain specialist": 0.08}[bg]
    qs_rank = [QS.index(q) for _, f, q in p["edu"] if q in QS and _ != "no degree"]
    best = min(qs_rank) if qs_rank else None
    s += {0: 0.28, 1: 0.14, 2: 0.05, 3: -0.04, 4: -0.06, None: 0.0}[best]
    has_phd = any(d == "PhD" for d, _, _ in p["edu"])
    if has_phd and it["name"] in DEEP_TECH:
        s += 0.15
    if any(j[2] == "5,000+" and j[3] in BIG for j in p["jobs"]):
        s += 0.12
    s += {"solo": -0.25, "1": 0.0, "2": 0.08, "3+": 0.04}[p["cof"]]
    outs = p["outs"]
    exits = [o for o in outs if o not in ("shut down", "operating")]
    if exits:
        s += max({"under $50M": 0.22, "$50M-$500M": 0.42, "$500M-$1B": 0.55, "over $1B": 0.6}[o]
                 for o in exits)
    elif outs:
        s += 0.05
    # Interactions (non-additive structure for the learn stages to find).
    if bg == "domain specialist" and p["indexp"] == "deep" and it["dom"] in SPECIALIST_DOMAINS:
        s += 0.2
    if bg == "technical" and it["name"] in DEEP_TECH and best == 0:
        s += 0.1
    if p["cof"] == "solo" and p["exp"] == "<5":
        s -= 0.2
    if bg == "business" and it["eff"] >= 0.1 and p["exp"] in ("10-15", "15+"):
        s += 0.1
    if exits and p["exp"] == "<5":
        s -= 0.1
    return s


def make_profile(rng):
    it = pick(rng, I, [x["w"] for x in I])
    bgs = ["technical", "business", "mixed", "domain specialist"]
    bg = pick(rng, bgs, list(it["bgw"]))
    track = it["tech"] or "product"
    if bg == "technical" and it["tech"] is None:
        bg = "business"
    if track == "product" and bg in ("technical", "mixed"):
        track = "software"
    cof = pick(rng, ["solo", "1", "2", "3+"], [14, 44, 26, 16])
    exp_b = pick(rng, ["<5", "5-10", "10-15", "15+"], [30, 33, 20, 17])
    lo, hi = {"<5": (0.5, 4.9), "5-10": (5, 9.9), "10-15": (10, 14.9), "15+": (15, 27)}[exp_b]
    years = rng.uniform(lo, hi)
    if bg == "domain specialist":
        indexp = pick(rng, ["deep", "some", "none"], [75, 25, 0])
    else:
        indexp = pick(rng, ["deep", "some", "none"], [24, 34, 42] if exp_b != "<5" else [12, 33, 55])
    outs = prior_startups(rng, exp_b)
    founder_jobs = sum(1 for _ in outs if rng.random() < 0.6)
    for _ in range(40):
        jobs, _ = make_jobs(rng, it, bg, track, years, indexp, founder_jobs)
        if check_indexp(it, jobs, indexp):
            break
    else:
        return None
    edu = make_edu(rng, bg, it, track)
    st, ex = startups_text(outs)
    return dict(it=it, bg=bg, track=track, cof=cof, exp=bucket_exp(sum(j[4] for j in jobs)),
                indexp=indexp, jobs=jobs, edu=edu, outs=outs, startups=st, exits=ex)


def mark_unknown(rng, p):
    """Mark 1 or 2 fields as unknown (about 15% of records)."""
    n = 1 if rng.random() < 0.72 else 2
    options = ["qs", "employees", "employees", "duration"]
    if p["outs"]:
        options += ["exits", "exits"]
    else:
        options += ["startups"]
    chosen = []
    while len(chosen) < n:
        o = pick(rng, options)
        if o == "startups":  # masks two fields (startups and exits) when n is 2
            chosen = ["startups"]
            break
        if o not in chosen:
            chosen.append(o)
    for o in chosen:
        if o == "qs":
            idx = [i for i, (d, f, q) in enumerate(p["edu"]) if q is not None]
            if idx:
                i = pick(rng, idx)
                d, f, _ = p["edu"][i]
                p["edu"][i] = (d, f, "unknown")
        elif o == "employees":
            j = pick(rng, p["jobs"])
            j[2] = "unknown"
        elif o == "duration":
            j = pick(rng, p["jobs"])
            j.append("unknown")
        elif o == "exits":
            p["exits"] = "unknown"
        elif o == "startups":
            p["startups"], p["exits"] = "unknown", "unknown" if n == 2 else "none"
    p["unknown"] = True


def render(p) -> str:
    it = p["it"]
    lines = [
        f"This founder leads a startup in the {it['name']} industry, founded with {p['cof']} "
        "co-founder(s).",
        f"Founder background: {p['bg']}, {p['exp']} years of work experience, {p['indexp']} prior "
        "experience in this startup's industry.",
        "Education:",
    ]
    for d, f, q in p["edu"]:
        lines.append("- no degree" if f is None else f"- {d} in {f}, university ranked QS {q}")
    lines.append("Jobs (oldest first):")
    for j in p["jobs"]:
        role, comp, size, label, d = j[:5]
        dur = "unknown" if len(j) > 5 else f"{bucket_dur(d)} years"
        sz = "unknown employees" if size == "unknown" else f"{size} employees"
        lines.append(f"- {role}, {comp}, {sz}, {label}, {dur}")
    lines.append(f"Prior startups: {p['startups']}.")
    lines.append(f"Prior exits: {p['exits']}.")
    return "\n".join(lines)


def shingles(text: str, k: int = 5) -> set[str]:
    toks = re.findall(r"\w+", text.lower())
    return {" ".join(toks[i:i + k]) for i in range(max(1, len(toks) - k + 1))}


def career_path(p) -> tuple:
    return tuple((normalise(j[0]), normalise(j[3])) for j in p["jobs"])


def block_counts(b: int) -> dict:
    """Outcome counts for synthetic block b (1-based); alternates 8/7 to total 450 each."""
    small = 8 if b % 2 == 0 else 7
    return {"over $1B": 5, "$500M-$1B": 5, "$50M-$500M": 15 - small, "under $50M": small,
            "shut down": 25}


def shuffle_block(rng, rows):
    while True:
        rng.shuffle(rows)
        run = longest = 1
        for a, b in zip(rows, rows[1:]):
            run = run + 1 if a["outcome"] == b["outcome"] else 1
            longest = max(longest, run)
        if longest <= 4:
            return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data/raw/full.jsonl"))
    ap.add_argument("--sample", default=str(ROOT / "data/raw/sample50.jsonl"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--noise", type=float, default=NOISE_SD)
    ap.add_argument("--meta", default=None, help="optional JSONL of per-row scores, for checks")
    args = ap.parse_args()
    rng = random.Random(args.seed)

    sample = [json.loads(ln) for ln in Path(args.sample).read_text().splitlines() if ln.strip()]
    seen_paths: set = set()
    seen_sh: list[set] = []
    out_rows, meta = [], []
    for r in sample:
        out_rows.append(r)
        seen_sh.append(shingles(r["input"]))
        meta.append({"source": "real", "score": None})

    for b in range(1, 60):
        block = []
        while len(block) < 50:
            p = make_profile(rng)
            if p is None:
                continue
            path = career_path(p)
            if path in seen_paths:
                continue
            score = background_score(p)  # on the true values, before any are masked
            if rng.random() < 0.15:
                mark_unknown(rng, p)
            text = render(p)
            sh = shingles(text)
            if any(len(sh & s) / len(sh | s) >= 0.7 for s in seen_sh):
                continue
            seen_paths.add(path)
            seen_sh.append(sh)
            p["text"], p["b"] = text, score
            p["z"] = p["b"] + rng.gauss(0, args.noise)
            block.append(p)
        counts = block_counts(b)
        ranked = sorted(block, key=lambda q: -q["z"])
        i = 0
        for band in ["over $1B", "$500M-$1B", "$50M-$500M", "under $50M", "shut down"]:
            for q in ranked[i:i + counts[band]]:
                q["outcome"] = band
                q["years"] = pick(rng, YEARS, YEARS_W[band])
            i += counts[band]
        for q in shuffle_block(rng, block):
            out_rows.append({"instruction": INSTRUCTION, "input": q["text"],
                             "output": f"outcome: {q['outcome']}\nyears: {q['years']}"})
            meta.append({"source": "synthetic", "score": round(q["b"], 4)})

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in out_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    if args.meta:
        with open(args.meta, "w", encoding="utf-8") as fh:
            for m in meta:
                fh.write(json.dumps(m) + "\n")
    print(f"wrote {len(out_rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
