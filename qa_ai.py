"""Local QA AI - no external LLM/API key required.
A lightweight NLP/ML engine trained from bundled QA examples. It classifies
requirements, extracts requirement-like sentences, and expands them into
positive, negative, validation, boundary, security and usability tests.
"""
import re
from typing import List, Dict

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

TRAINING = [
    ("user can login with email and password", "authentication"),
    ("registered user signs in and logs out", "authentication"),
    ("password must be valid to access account", "authentication"),
    ("new users can register an account", "registration"),
    ("email must be unique during registration", "registration"),
    ("user submits required form fields", "form"),
    ("name email and phone are required", "form"),
    ("invalid email format should be rejected", "validation"),
    ("field accepts minimum and maximum length", "validation"),
    ("admin can manage users and roles", "authorization"),
    ("only authorized users can access dashboard", "authorization"),
    ("user can search and filter records", "search"),
    ("results can be sorted and filtered", "search"),
    ("user uploads a document or file", "upload"),
    ("unsupported file type is rejected", "upload"),
    ("customer adds item to cart and checks out", "commerce"),
    ("payment is processed after checkout", "commerce"),
    ("system sends notification after an action", "notification"),
    ("application exposes an api endpoint", "api"),
    ("api returns json response and status code", "api"),
    ("page should work on mobile and desktop", "responsive"),
    ("application displays error message when server fails", "error_handling"),
    ("user can reset password using email verification", "authentication"),
    ("account locks after repeated failed login attempts", "authentication"),
    ("user confirms email after creating an account", "registration"),
    ("registration password and confirmation must match", "registration"),
    ("form accepts a phone number in the documented format", "form"),
    ("required field cannot be submitted empty", "validation"),
    ("date must be within the allowed range", "validation"),
    ("manager can approve requests but normal users cannot", "authorization"),
    ("search results should support pagination", "search"),
    ("filter should persist while navigating results", "search"),
    ("uploaded files must be scanned before processing", "upload"),
    ("downloaded report is generated after upload", "upload"),
    ("order total includes applicable tax", "commerce"),
    ("failed payment should not create a completed order", "commerce"),
    ("email notification is sent after successful registration", "notification"),
    ("api endpoint requires bearer authentication", "api"),
    ("api rejects malformed json payload", "api"),
    ("page controls are usable on small screens", "responsive"),
    ("application shows a friendly 404 page", "error_handling"),
    ("discount is applied according to the business rule", "business_rule"),
]

TEMPLATES = {
    "authentication": [
        ("Positive", "Valid login", "Enter valid registered credentials and submit the login form.", "The user is authenticated and the documented authenticated page is displayed."),
        ("Negative", "Invalid login", "Enter a registered email with an incorrect password and submit.", "Login is rejected and a clear, non-sensitive error is shown."),
        ("Validation", "Empty login fields", "Submit the login form with required fields empty.", "Required-field validation is displayed and authentication is not attempted."),
        ("Security", "Protected page access", "Open a protected URL without an authenticated session.", "Access is denied or the user is redirected to the authentication page."),
        ("Security", "Logout session invalidation", "Log in, log out, then revisit a protected page.", "The previous session cannot access protected content."),
    ],
    "registration": [
        ("Positive", "Valid registration", "Enter valid unique registration data and submit.", "The account is created according to the documented workflow."),
        ("Negative", "Duplicate account", "Register using an email or identifier already registered.", "Registration is rejected with a clear duplicate-account message."),
        ("Validation", "Invalid registration data", "Enter malformed or missing required registration values.", "Invalid data is rejected and useful validation messages are shown."),
    ],
    "form": [
        ("Positive", "Valid form submission", "Complete all required fields with valid values and submit.", "The form is accepted and the documented success action occurs."),
        ("Negative", "Missing required fields", "Submit the form with one or more required fields empty.", "Submission is blocked and each missing required field is identified."),
        ("Validation", "Whitespace input", "Enter only spaces in required text fields and submit.", "Whitespace-only values are rejected when the field requires meaningful text."),
    ],
    "validation": [
        ("Validation", "Boundary value validation", "Test the minimum, maximum, just-below-minimum and just-above-maximum values supported by the requirement.", "Values inside the allowed range are accepted and out-of-range values are rejected."),
        ("Negative", "Malformed input", "Enter a malformed value such as an invalid email, unexpected characters, or an invalid format.", "The application rejects the value without crashing or accepting invalid data."),
    ],
    "authorization": [
        ("Security", "Role-based access", "Sign in with each documented role and open the protected feature.", "Each role can access only the functionality permitted by the requirement."),
        ("Negative", "Unauthorized action", "Attempt a protected action with a user lacking the required permission.", "The action is denied and no protected data is changed."),
    ],
    "search": [
        ("Positive", "Search exact match", "Search for an existing record using a valid exact keyword.", "The expected matching record is returned."),
        ("Edge", "Search no-result term", "Search using a valid term that has no matching record.", "The application displays an accurate empty-result state without errors."),
        ("Edge", "Search special characters", "Search using spaces and supported special characters.", "The search is handled safely and results remain correct."),
    ],
    "upload": [
        ("Positive", "Supported file upload", "Upload a valid supported file within the documented size limit.", "The file is accepted and processed according to the requirement."),
        ("Negative", "Unsupported file upload", "Upload a file type that is not documented as supported.", "The upload is rejected safely with a clear message."),
        ("Edge", "Maximum file size", "Upload files at, just below, and just above the documented size limit.", "Files within the limit are accepted and oversized files are rejected."),
    ],
    "commerce": [
        ("Positive", "Checkout happy path", "Add the required item/service and complete checkout with valid test data.", "The order/payment completes according to the documented business flow."),
        ("Negative", "Invalid checkout data", "Attempt checkout with missing or invalid required data.", "Checkout is blocked and the user receives actionable validation feedback."),
        ("Edge", "Cart quantity boundary", "Test minimum, maximum and invalid quantities permitted by the requirement.", "Allowed quantities are processed correctly and invalid quantities are rejected."),
    ],
    "notification": [
        ("Positive", "Expected notification", "Perform the documented action that triggers a notification.", "The notification is generated for the correct event and recipient."),
    ],
    "api": [
        ("Positive", "API success response", "Send a valid request to the documented endpoint.", "The API returns the documented success status and response structure."),
        ("Negative", "API invalid request", "Send a request with missing, malformed, or invalid parameters.", "The API returns an appropriate error status and does not expose sensitive details."),
        ("Security", "API unauthorized access", "Call a protected endpoint without valid authorization.", "The API denies access and returns the documented authorization response."),
    ],
    "responsive": [
        ("Usability", "Responsive layout", "Open key screens at mobile, tablet and desktop viewport sizes.", "Content remains readable, controls remain usable, and no critical overlap occurs."),
    ],
    "error_handling": [
        ("Negative", "Server/network failure", "Trigger or simulate a network/server failure during a normal operation.", "A user-friendly error is shown and sensitive implementation details are not exposed."),
    ],
    "business_rule": [
        ("Business Rule", "Business rule calculation", "Execute the documented business rule with normal, boundary and invalid inputs.", "The result matches the documented rule for every tested input."),
    ],
}

class LocalQATestAI:
    def __init__(self):
        self.vectorizer = None
        self.model = None
        if SKLEARN_AVAILABLE:
            texts = [x[0] for x in TRAINING]
            labels = [x[1] for x in TRAINING]
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True, sublinear_tf=True)
            X = self.vectorizer.fit_transform(texts)
            self.model = LogisticRegression(max_iter=1000, random_state=42)
            self.model.fit(X, labels)

    def split_requirements(self, text: str) -> List[str]:
        text = re.sub(r"\r", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        chunks = re.split(r"(?<=[.!?])\s+|\n+|(?<=;)\s+", text)
        out = []
        for c in chunks:
            c = c.strip(" -*•\t")
            if 20 <= len(c) <= 500:
                out.append(c)
        return list(dict.fromkeys(out))

    def classify(self, sentence: str) -> str:
        s = sentence.lower()
        if self.model:
            pred = self.model.predict(self.vectorizer.transform([sentence]))[0]
        else:
            pred = "form"
        # Strong keyword overrides improve precision for explicit requirements.
        rules = [
            ("authentication", ["login", "log in", "sign in", "password", "logout", "log out"]),
            ("registration", ["register", "registration", "sign up", "signup", "create account"]),
            ("authorization", ["role", "permission", "admin", "authorized", "access control"]),
            ("upload", ["upload", "file type", "document", "attachment"]),
            ("search", ["search", "filter", "sort"]),
            ("commerce", ["payment", "checkout", "cart", "order", "purchase"]),
            ("api", ["api", "endpoint", "request", "response", "http status"]),
            ("responsive", ["mobile", "desktop", "responsive", "viewport"]),
            ("validation", ["validation", "minimum", "maximum", "format", "length", "required"]),
            ("notification", ["notification", "email alert", "sms alert"]),
        ]
        for label, words in rules:
            if any(w in s for w in words):
                return label
        return pred

    def generate(self, document: str, website: str = "") -> List[Dict[str, str]]:
        sentences = self.split_requirements(document[:100000])
        cases: List[Dict[str, str]] = []
        seen = set()
        # First generate tests directly from detected requirement categories.
        categories = []
        for s in sentences:
            cat = self.classify(s)
            if cat not in categories:
                categories.append(cat)
        # Ensure baseline quality checks for every web project.
        for baseline in ("responsive", "error_handling"):
            if baseline not in categories:
                categories.append(baseline)
        for cat in categories:
            for kind, title, steps, expected in TEMPLATES.get(cat, []):
                key = title.lower()
                if key not in seen:
                    seen.add(key)
                    cases.append({"title": f"{title} — {cat.replace('_', ' ').title()}", "steps": steps, "expected_result": expected})
        # Requirement-specific cases preserve document meaning instead of hallucinating features.
        for sentence in sentences:
            cat = self.classify(sentence)
            if len(sentence) < 25:
                continue
            base = re.sub(r"\s+", " ", sentence).rstrip(".")
            candidates = [
                ("Requirement verification", f"Verify the documented requirement: {base}.", "The application behaves exactly as described by the project requirement."),
                ("Requirement negative", f"Attempt the documented flow with an invalid, missing, or unsupported input related to: {base}.", "The invalid condition is handled safely and the requirement is not violated."),
            ]
            if cat in {"validation", "form", "registration"}:
                candidates.append(("Boundary verification", f"Test the lowest, highest, empty and representative valid values relevant to: {base}.", "Boundary values follow the documented constraints and invalid values are rejected."))
            for suffix, steps, expected in candidates:
                title = f"{suffix} — {base[:180]}"
                key = title.lower()
                if key not in seen:
                    seen.add(key)
                    cases.append({"title": title[:255], "steps": steps, "expected_result": expected})
        # Limit to a useful report size.
        return cases[:80]

ENGINE = LocalQATestAI()
