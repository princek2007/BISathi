import json
import os
import time
import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pydantic import BaseModel

from bis_standards_service import search_bis_standards


load_dotenv()


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# ============================================================
# FILE PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PRODUCTS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "products.json"
)

BIS_KNOWLEDGE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "bis_knowledge.json"
)


# ============================================================
# OFFICIAL BIS SOURCES
# ============================================================

BIS_OFFICIAL_SOURCES = {
    "home": {
        "title": "BIS Official Website",
        "url": "https://www.bis.gov.in/"
    },

    "standards": {
        "title": "BIS Standards Portal - Know Your Standards",
        "url": "https://standards.bis.gov.in/"
    },

    "certification_process": {
        "title": "BIS Product Certification Process",
        "url": "https://www.bis.gov.in/product-certification/product-certification-process/?lang=en"
    },

    "apply_license": {
        "title": "BIS - Apply For License",
        "url": "https://www.bis.gov.in/apply-for-a-license/?lang=en"
    },

    "compulsory_certification": {
        "title": "BIS - Products Under Compulsory Certification",
        "url": "https://www.bis.gov.in/product-certification/products-under-compulsory-certification/?lang=en"
    },

    "certification_faq": {
        "title": "BIS Product Certification FAQ",
        "url": "https://www.bis.gov.in/product-certification/product-certification-faq/?lang=en"
    },

    "bis_care": {
        "title": "BIS CARE App",
        "url": "https://www.bis.gov.in/bis-apps/?lang=en"
    },

    "consumer_faq": {
        "title": "BIS Consumer FAQ",
        "url": "https://www.bis.gov.in/consumer-overview/for-consumers-faq/?lang=en"
    },
}


SOURCE_MAPPINGS = {
    "standards": [
        "standards",
        "home"
    ],

    "certification": [
        "apply_license",
        "certification_process",
        "compulsory_certification"
    ],

    "documents": [
        "apply_license",
        "certification_process",
        "certification_faq"
    ],

    "isi": [
        "bis_care",
        "consumer_faq",
        "standards",
        "certification_process"
    ],

    "consumer": [
        "bis_care",
        "consumer_faq",
        "home"
    ],
}


def get_official_sources(source_type="general"):

    keys = SOURCE_MAPPINGS.get(
        source_type,
        [
            "home",
            "standards",
            "bis_care"
        ]
    )

    return [
        BIS_OFFICIAL_SOURCES[k]
        for k in keys
    ]


# ============================================================
# JSON HELPERS
# ============================================================

def load_json_file(
    file_path,
    default=None
):

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"Error loading {file_path}: {e}"
        )

        return (
            []
            if default is None
            else default
        )


def load_products():

    return load_json_file(
        PRODUCTS_FILE,
        []
    )


def load_bis_knowledge():

    data = load_json_file(
        BIS_KNOWLEDGE_FILE,
        []
    )

    if isinstance(data, dict):

        return (
            data.get("knowledge")
            or data.get("items")
            or [data]
        )

    return (
        data
        if isinstance(data, list)
        else []
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):

    return (
        " ".join(
            str(text)
            .lower()
            .strip()
            .split()
        )
        if text
        else ""
    )


def find_product(product_name: str):

    search_text = normalize_text(
        product_name
    )

    if not search_text:
        return None

    for product in load_products():

        name = normalize_text(
            product.get(
                "product",
                ""
            )
        )

        keywords = [
            normalize_text(k)
            for k in product.get(
                "keywords",
                []
            )
        ]

        if (
            search_text == name
            or search_text in keywords
        ):

            return product

        if (
            search_text in name
            or any(
                search_text in kw
                or kw in search_text
                for kw in keywords
                if kw
            )
        ):

            return product

    return None


# ============================================================
# BIS KNOWLEDGE SEARCH
# ============================================================

def find_bis_knowledge(question):

    search_text = normalize_text(
        question
    )

    if not search_text:
        return None

    best_item = None
    best_score = 0

    for item in load_bis_knowledge():

        score = 0

        q = normalize_text(
            item.get(
                "question",
                ""
            )
        )

        title = normalize_text(
            item.get(
                "title",
                ""
            )
        )

        kw_list = item.get(
            "keywords",
            []
        )

        keywords = [
            normalize_text(k)
            for k in (
                kw_list
                if isinstance(
                    kw_list,
                    list
                )
                else [kw_list]
            )
        ]

        var_list = item.get(
            "question_variants",
            []
        )

        variants = [
            normalize_text(v)
            for v in (
                var_list
                if isinstance(
                    var_list,
                    list
                )
                else [var_list]
            )
        ]

        searchable_text = normalize_text(
            f"{item.get('id', '')} "
            f"{q} "
            f"{title} "
            f"{' '.join(keywords)} "
            f"{' '.join(variants)}"
        )

        if q and search_text == q:
            score += 100

        if title and search_text == title:
            score += 90

        if (
            len(search_text) >= 4
            and search_text in searchable_text
        ):
            score += 70

        for kw in keywords:

            if not kw:
                continue

            if search_text == kw:
                score += 80

            elif (
                len(kw) >= 4
                and kw in search_text
            ):
                score += 40

            elif (
                len(search_text) >= 4
                and search_text in kw
            ):
                score += 35

        for v in variants:

            if not v:
                continue

            if search_text == v:
                score += 90

            elif (
                len(v) >= 4
                and v in search_text
            ):
                score += 45

            elif (
                len(search_text) >= 4
                and search_text in v
            ):
                score += 40

        if score > best_score:

            best_score = score
            best_item = item

    return (
        best_item
        if best_score >= 35
        else None
    )


def build_bis_knowledge_response(
    item,
    user_type
):

    if (
        user_type
        in [
            "industry",
            "manufacturer"
        ]
        and item.get(
            "industry_answer"
        )
    ):

        return item[
            "industry_answer"
        ]

    if (
        user_type
        not in [
            "industry",
            "manufacturer"
        ]
        and item.get(
            "consumer_answer"
        )
    ):

        return item[
            "consumer_answer"
        ]

    return item.get(
        "answer"
    )


def get_knowledge_source_type(
    item,
    user_type
):

    st = item.get(
        "source_type"
    )

    if st in [
        "standards",
        "certification",
        "documents",
        "isi",
        "consumer",
        "general"
    ]:

        return st

    return (
        "certification"
        if user_type
        in [
            "industry",
            "manufacturer"
        ]
        else "consumer"
    )


# ============================================================
# PRODUCT RESPONSE
# ============================================================

def clean_product_response(
    answer: str
):

    if not answer:
        return answer

    cleaned = []
    prev_blank = False

    for raw_line in answer.splitlines():

        line = raw_line.strip()

        if line in [
            "---",
            "\\---"
        ]:
            continue

        line = (
            line
            .replace("\\*", "*")
            .replace("\\_", "_")
        )

        parts = line.split(
            " ",
            1
        )

        if (
            len(parts) == 2
            and parts[0][:-1].isdigit()
            and parts[0][-1]
            in [".", ")"]
        ):

            line = f"- {parts[1]}"

        if line == "":

            if prev_blank:
                continue

            prev_blank = True

        else:

            prev_blank = False

        cleaned.append(line)

    return "\n".join(
        cleaned
    ).strip()


def build_product_response(
    product_data,
    user_type
):

    p_name = product_data.get(
        "product",
        "Product"
    )

    std = product_data.get(
        "standard",
        ""
    )

    title = product_data.get(
        "standard_title",
        ""
    )

    cert = product_data.get(
        "certification",
        ""
    )

    checks = (
        product_data.get(
            "industry_guidance",
            []
        )
        if user_type
        in [
            "industry",
            "manufacturer"
        ]
        else product_data.get(
            "consumer_checks",
            []
        )
    )

    verif = product_data.get(
        "verification",
        ""
    )

    lines = [
        "## Product",
        "",
        p_name,
        "",
        "## Relevant BIS / Indian Standard Guidance",
        ""
    ]

    if std:

        lines.append(
            f"- {std}: {title}"
            if title
            else f"- {std}"
        )

    lines.extend([
        "",
        "## Certification / Compliance",
        ""
    ])

    if cert:

        lines.append(
            f"- {cert}"
        )

    lines.extend([
        "",
        "## What to Check",
        ""
    ])

    lines.extend(
        [
            f"- {c}"
            for c in checks
        ]
    )

    if verif:

        lines.extend([
            "",
            "## Important",
            "",
            verif
        ])

    return "\n".join(
        lines
    )


# ============================================================
# LIVE BIS RESPONSE
# ============================================================

def build_live_bis_standard_response(
    standards,
    product,
    user_type
):

    lines = [
        "## Product",
        "",
        product,
        "",
        "## Relevant BIS / Indian Standard Guidance",
        ""
    ]

    for s in standards:

        num = s.get(
            "standard_number"
        )

        name = s.get(
            "standard_name"
        )

        if not num and not name:
            continue

        if num and name:

            lines.append(
                f"- **{num}** — {name}"
            )

        elif num:

            lines.append(
                f"- **{num}**"
            )

        else:

            lines.append(
                f"- {name}"
            )

        dates = []

        if s.get("published_on"):

            dates.append(
                f"Published: {s['published_on']}"
            )

        if s.get("valid_upto"):

            dates.append(
                f"Valid upto: {s['valid_upto']}"
            )

        if dates:

            lines.append(
                f"  - {' | '.join(dates)}"
            )

        if s.get("withdraw_status"):

            w_text = "- Status: Withdrawn"

            if s.get("withdraw_on"):

                w_text += (
                    f" | Withdrawn on: "
                    f"{s['withdraw_on']}"
                )

            lines.append(
                f"  {w_text}"
            )

    lines.extend([
        "",
        "## Certification / Compliance",
        "",
        "- The live BIS search results identify standards relevant to the entered product.",
        "- Whether a product is subject to mandatory certification or other regulatory requirements must be checked against current BIS requirements and Quality Control Orders (QCOs).",
        "",
        "## What to Check",
        "",
        "- Review the relevant Indian Standard for the exact product.",
        "- Check current BIS requirements applicable to the product.",
        "- Check whether the relevant standard is current, revised or withdrawn.",
        "- For certification or licensing decisions, verify the latest information through official BIS sources.",
        "",
        "## Important",
        "",
        "These standards were retrieved from the live BIS Know Your Standards service. The search result itself does not establish mandatory BIS certification."
    ])

    return "\n".join(
        lines
    )


# ============================================================
# PRODUCT-COMPLIANCE QUESTION DETECTION
# ============================================================

def is_product_compliance_question(
    question: str
):

    q = normalize_text(
        question
    )

    if not q:
        return False

    compliance_terms = [
        "compliance",
        "certification",
        "certificate",
        "standard",
        "standards",
        "requirement",
        "requirements",
        "mandatory",
        "license",
        "licence",
        "isi",
        "qco",
        "quality control order",
        "bis approval",
        "bis certification",
        "bis requirement",
        "bis standard",
    ]

    generic_questions = [
        "what is bis",
        "what's bis",
        "what is the bis",
        "what is bureau of indian standards",
        "what is the bureau of indian standards",
        "what are indian standards",
        "what is an indian standard",
        "what services does bis provide",
        "services of bis",
    ]

    if q in generic_questions:
        return False

    return any(
        term in q
        for term in compliance_terms
    )


# ============================================================
# EXTRACT PRODUCT FROM COMPLIANCE QUESTION
# ============================================================

def extract_product_from_question(
    question: str
):

    q = normalize_text(
        question
    )

    if not q:
        return ""

    for product in load_products():

        product_name = normalize_text(
            product.get(
                "product",
                ""
            )
        )

        keywords = [
            normalize_text(k)
            for k in product.get(
                "keywords",
                []
            )
        ]

        candidates = [
            product_name
        ] + keywords

        for candidate in candidates:

            if (
                candidate
                and len(candidate) >= 3
                and candidate in q
            ):

                return product_name

    removable_patterns = [
        r"\bdoes\b",
        r"\bdo\b",
        r"\bis\b",
        r"\bare\b",
        r"\bthe\b",
        r"\ba\b",
        r"\ban\b",
        r"\bmy\b",
        r"\bthis\b",
        r"\bthat\b",
        r"\bneed\b",
        r"\bneeds\b",
        r"\brequire\b",
        r"\brequires\b",
        r"\brequired\b",
        r"\bfor\b",
        r"\bunder\b",
        r"\bwith\b",
        r"\bhave\b",
        r"\bhas\b",
        r"\bget\b",
        r"\bgetting\b",
        r"\bobtain\b",
        r"\bobtaining\b",
        r"\bcheck\b",
        r"\bchecks\b",
        r"\bchecking\b",
        r"\bapplicable\b",
        r"\bmandatory\b",
        r"\bcompliance\b",
        r"\bcertification\b",
        r"\bcertificate\b",
        r"\bcertified\b",
        r"\bstandard\b",
        r"\bstandards\b",
        r"\brequirement\b",
        r"\brequirements\b",
        r"\blicense\b",
        r"\blicence\b",
        r"\bisi\b",
        r"\bmark\b",
        r"\bqco\b",
        r"\bquality control order\b",
        r"\bbis\b",
        r"\bapproval\b",
        r"\bapproved\b",
    ]

    result = q

    for pattern in removable_patterns:

        result = re.sub(
            pattern,
            " ",
            result
        )

    result = re.sub(
        r"[^a-z0-9\s\-]",
        " ",
        result
    )

    result = " ".join(
        result.split()
    ).strip()

    return result


# ============================================================
# GEMINI COMPLIANCE RESPONSE
# ============================================================

COMPLIANCE_PROMPT = """You are BISathi, an AI-powered assistant for Indian Standards and BIS services.

The user has asked a product-specific BIS compliance question.

IMPORTANT RULES:
1. The BIS search results below come from the official BIS Know Your Standards service.
2. Use these retrieved BIS records as the primary factual grounding for Indian Standard numbers and titles.
3. Do NOT invent standard numbers.
4. Do NOT claim that BIS certification is mandatory merely because a standard exists.
5. Do NOT invent QCO applicability.
6. If mandatory certification cannot be established from the retrieved information, clearly say that current BIS requirements and applicable QCOs must be checked.
7. Explain the retrieved standards in practical language.
8. Adapt the answer for the specified user type.
9. Do not say that you independently verified information that is not present in the supplied BIS records.

Use these sections:

## Product

## Relevant BIS / Indian Standard Guidance

## Certification / Compliance

## What to Check

## Important

Use clean Markdown and '-' bullets.
"""


def build_gemini_compliance_prompt(
    question,
    product,
    user_type,
    standards
):

    standards_text = []

    for s in standards:

        standard_number = s.get(
            "standard_number",
            ""
        )

        standard_name = s.get(
            "standard_name",
            ""
        )

        published_on = s.get(
            "published_on",
            ""
        )

        valid_upto = s.get(
            "valid_upto",
            ""
        )

        withdraw_status = s.get(
            "withdraw_status",
            ""
        )

        record = (
            f"Standard Number: {standard_number}\n"
            f"Standard Name: {standard_name}\n"
            f"Published On: {published_on}\n"
            f"Valid Upto: {valid_upto}\n"
            f"Withdraw Status: {withdraw_status}"
        )

        standards_text.append(
            record
        )

    return (
        f"{COMPLIANCE_PROMPT}\n\n"
        f"User Type:\n{user_type}\n\n"
        f"User Question:\n{question}\n\n"
        f"Product:\n{product}\n\n"
        f"OFFICIAL BIS LIVE SEARCH RESULTS:\n\n"
        f"{chr(10).join(standards_text)}"
    )


# ============================================================
# LIVE COMPLIANCE FALLBACK
# ============================================================

def build_live_compliance_fallback(
    standards,
    product,
    user_type,
    product_data=None
):

    live_answer = build_live_bis_standard_response(
        standards,
        product,
        user_type
    )

    if not product_data:
        return live_answer

    local_answer = build_product_response(
        product_data,
        user_type
    )

    return (
        live_answer
        + "\n\n"
        + "## BISathi Local Product Guidance"
        + "\n\n"
        + local_answer
    )


# ============================================================
# CERTIFICATION GUIDANCE
# ============================================================

def build_certification_guidance(
    product_data,
    user_type
):

    p_name = product_data.get(
        "product",
        "your product"
    )

    std = product_data.get(
        "standard",
        ""
    )

    title = product_data.get(
        "standard_title",
        ""
    )

    verif = product_data.get(
        "verification",
        ""
    )

    is_ind = user_type in [
        "industry",
        "manufacturer"
    ]

    lines = [
        "## BIS Certification Guidance",
        "",
        f"Guidance for **{p_name}**.",
        ""
    ]

    if is_ind:

        lines.extend([
            "## Recommended Path",
            "",
            "1. Identify the exact product category and intended use.",
            "2. Identify the applicable Indian Standard.",
            "3. Check applicability under BIS requirements, Quality Control Orders (QCOs), or regulations.",
            "4. Review applicable testing, documentation, and assessment requirements.",
            "5. Complete product testing and assessment.",
            "6. Follow the applicable BIS application and licensing process.",
            "7. Complete inspection, evaluation, or assessment requirements.",
            "8. Maintain compliance post-licensing."
        ])

    else:

        lines.extend([
            "## For Consumers",
            "",
            "- First identify the exact product and its applicable standard.",
            "- Check whether BIS certification or marking is applicable.",
            "- Check relevant BIS marking and certification info where applicable.",
            "- Verify certification or licence info using official BIS resources."
        ])

    lines.extend([
        "",
        "## Product Standard",
        ""
    ])

    lines.append(
        f"- {std}: {title}"
        if std and title
        else f"- {std}"
        if std
        else "- The applicable Indian Standard must be determined for the exact product."
    )

    lines.extend([
        "",
        "## Important",
        "",
        "The exact certification pathway, documents, testing, fees, inspection requirements, and applicability vary by product.",
        verif if verif else "",
        "Always verify the latest applicable requirements through official BIS information before starting a certification process."
    ])

    return "\n".join(
        filter(None, lines)
    )


# ============================================================
# DOCUMENT CHECKLIST
# ============================================================

def convert_checklist_item(item):

    if isinstance(item, str):

        return item.strip()

    if isinstance(item, dict):

        return (
            item.get("document")
            or item.get("name")
            or item.get("title")
            or item.get("description")
            or item.get("text")
            or ""
        ).strip()

    return str(item).strip()


def get_local_document_checklist(
    product_data,
    user_type
):

    if not product_data:
        return []

    is_ind = user_type in [
        "industry",
        "manufacturer"
    ]

    checklist = []

    possible_fields = (
        [
            "document_checklist",
            "documents",
            "industry_documents",
            "industry_guidance"
        ]
        if is_ind
        else
        [
            "document_checklist",
            "documents",
            "consumer_document_checks",
            "consumer_checks"
        ]
    )

    for field in possible_fields:

        value = product_data.get(
            field,
            []
        )

        if isinstance(value, list):

            for item in value:

                text = convert_checklist_item(
                    item
                )

                if text:
                    checklist.append(text)

        if checklist:
            break

    return checklist


def get_default_document_checklist(
    user_type
):

    is_ind = user_type in [
        "industry",
        "manufacturer"
    ]

    if is_ind:

        return [
            "Exact product name, model and product description.",
            "Manufacturer / manufacturing-unit details.",
            "Applicable Indian Standard details.",
            "Product technical specifications.",
            "Product drawings, specifications or technical documents where applicable.",
            "Manufacturing process information.",
            "Quality-control and inspection information.",
            "Details of raw materials or components where applicable.",
            "Testing requirements and relevant test reports where applicable.",
            "Details of in-house testing facilities or test equipment where applicable.",
            "Calibration records for relevant testing equipment where applicable.",
            "Packaging, marking and labelling information.",
            "Documents and information required for the applicable BIS application or licensing process."
        ]

    return [
        "Exact product name and product category.",
        "Manufacturer / brand information.",
        "Applicable Indian Standard information.",
        "BIS / ISI marking information where applicable.",
        "Licence / certification details where applicable.",
        "Product label and packaging information.",
        "Model or identification details.",
        "Official BIS information for verification."
    ]


def build_document_checklist(
    product_data,
    user_type,
    live_standards=None,
    product_name=None
):

    live_standards = (
        live_standards
        if isinstance(
            live_standards,
            list
        )
        else []
    )

    p_name = (
        product_data.get(
            "product"
        )
        if product_data
        else product_name
        or "your product"
    )

    std = (
        product_data.get(
            "standard",
            ""
        )
        if product_data
        else ""
    )

    title = (
        product_data.get(
            "standard_title",
            ""
        )
        if product_data
        else ""
    )

    verif = (
        product_data.get(
            "verification",
            ""
        )
        if product_data
        else ""
    )

    local_checklist = get_local_document_checklist(
        product_data,
        user_type
    )

    if local_checklist:

        checklist = local_checklist

        checklist_source = (
            "official_bis_live_search + local_product_data"
        )

    else:

        checklist = get_default_document_checklist(
            user_type
        )

        checklist_source = (
            "official_bis_live_search + BISathi default guidance"
            if live_standards
            else "BISathi default guidance"
        )

    unique_checklist = []

    seen = set()

    for item in checklist:

        normalized = normalize_text(
            item
        )

        if (
            normalized
            and normalized not in seen
        ):

            seen.add(normalized)

            unique_checklist.append(
                item
            )

    checklist = unique_checklist

    lines = [
        "## BIS Document Checklist",
        "",
        f"General document and information checklist for **{p_name}**.",
        "",
        "## Data Sources",
        "",
        "- Official BIS live standards search.",
        "- BISathi local product data.",
        "- BISathi product-document guidance.",
        ""
    ]

    if live_standards:

        lines.extend([
            "## Official BIS Standards Found",
            ""
        ])

        for standard in live_standards:

            standard_number = standard.get(
                "standard_number"
            )

            standard_name = standard.get(
                "standard_name"
            )

            if (
                not standard_number
                and not standard_name
            ):
                continue

            if (
                standard_number
                and standard_name
            ):

                lines.append(
                    f"- **{standard_number}** — {standard_name}"
                )

            elif standard_number:

                lines.append(
                    f"- **{standard_number}**"
                )

            else:

                lines.append(
                    f"- {standard_name}"
                )

        lines.append("")

    elif std:

        lines.extend([
            "## Product Standard",
            "",
            (
                f"- {std}: {title}"
                if title
                else f"- {std}"
            ),
            ""
        ])

    else:

        lines.extend([
            "## Product Standard",
            "",
            "- The applicable Indian Standard should be confirmed for the exact product.",
            ""
        ])

    lines.extend([
        "## Required Documents & Information",
        ""
    ])

    for item in checklist:

        lines.append(
            f"- {item}"
        )

    if verif:

        lines.extend([
            "",
            "## Product Verification Guidance",
            "",
            verif
        ])

    lines.extend([
        "",
        "## Important",
        "",
        "This checklist is preliminary guidance based on official BIS search results and BISathi local product information.",
        "The existence of an Indian Standard does not by itself establish that every document listed is mandatory.",
        "Exact documents may vary according to the product, applicable certification scheme, testing requirements and current BIS procedures.",
        "Confirm the latest applicable requirements with official BIS information before submission."
    ])

    return {
        "answer": "\n".join(lines),
        "checklist": checklist,
        "checklist_total": len(checklist),
        "checklist_completed": 0,
        "checklist_source": checklist_source
    }


# ============================================================
# ISI VERIFICATION
# ============================================================

def build_isi_local_summary(
    product_data,
    user_type
):

    if not product_data:

        return {
            "matched": False,
            "product": None,
            "standard": None,
            "standard_title": None,
            "certification": None,
            "verification": None
        }

    return {
        "matched": True,
        "product": product_data.get(
            "product"
        ),
        "standard": product_data.get(
            "standard"
        ),
        "standard_title": product_data.get(
            "standard_title"
        ),
        "certification": product_data.get(
            "certification"
        ),
        "verification": product_data.get(
            "verification"
        )
    }


def build_isi_bis_context(
    standards
):

    if not standards:

        return (
            "No matching records were returned "
            "by the official BIS live search."
        )

    records = []

    for standard in standards:

        records.append(
            "\n".join([
                f"Standard Number: {standard.get('standard_number', '')}",
                f"Standard Name: {standard.get('standard_name', '')}",
                f"Published On: {standard.get('published_on', '')}",
                f"Valid Upto: {standard.get('valid_upto', '')}",
                f"Withdraw Status: {standard.get('withdraw_status', '')}",
                f"Withdraw On: {standard.get('withdraw_on', '')}",
                f"Status: {standard.get('status', '')}"
            ])
        )

    return "\n\n".join(
        records
    )


ISI_GEMINI_PROMPT = """You are BISathi's ISI verification assistant.

The official BIS Know Your Standards service was searched for the user's entered product.

Your task is to explain the retrieved BIS information clearly.

IMPORTANT:
1. Treat the supplied official BIS search records as the primary factual source.
2. Do NOT invent an IS number, standard number, licence number, CM/L number, certification status, or QCO.
3. A standard appearing in BIS search results does NOT by itself prove that a particular product is certified.
4. Do NOT claim that a product is BIS certified unless the supplied data actually establishes that.
5. Clearly distinguish:
   - standard found
   - local BISathi product information
   - certification information
   - information that still needs official verification
6. If the official BIS search returns no result, clearly say so.
7. Keep the explanation practical for a consumer.
8. Do not claim that you performed a certificate/licence verification if the supplied data only contains standard-search records.

Use exactly these sections:

## Verification Summary

## Official BIS Search Result

## BISathi Product Database

## What This Means

## Important

Use clean Markdown and '-' bullets.
"""


def build_isi_gemini_prompt(
    product,
    standards,
    product_data
):

    local_summary = build_isi_local_summary(
        product_data,
        "consumer"
    )

    return (
        f"{ISI_GEMINI_PROMPT}\n\n"
        f"USER INPUT:\n"
        f"{product}\n\n"
        f"OFFICIAL BIS LIVE SEARCH RESULTS:\n"
        f"{build_isi_bis_context(standards)}\n\n"
        f"BISATHI LOCAL JSON RESULT:\n"
        f"{json.dumps(local_summary, indent=2)}"
    )


def build_isi_verification_result(
    product,
    standards,
    product_data,
    gemini_answer=None
):

    live_found = bool(
        standards
    )

    local_found = bool(
        product_data
    )

    if (
        live_found
        and local_found
    ):

        verification_status = (
            "BIS STANDARD FOUND + LOCAL PRODUCT MATCH"
        )

    elif live_found:

        verification_status = (
            "BIS STANDARD FOUND + LOCAL PRODUCT NOT FOUND"
        )

    elif local_found:

        verification_status = (
            "LOCAL PRODUCT MATCH + BIS LIVE RESULT NOT FOUND"
        )

    else:

        verification_status = (
            "NO MATCHING BIS OR LOCAL PRODUCT RECORD FOUND"
        )

    if gemini_answer:

        answer = clean_product_response(
            gemini_answer
        )

    else:

        lines = [
            "## Verification Summary",
            "",
            f"- **Input:** {product}",
            f"- **Status:** {verification_status}",
            ""
        ]

        lines.extend([
            "## Official BIS Search Result",
            ""
        ])

        if live_found:

            lines.append(
                f"- Official BIS returned **{len(standards)} matching record(s)."
            )

            for standard in standards:

                number = standard.get(
                    "standard_number"
                )

                name = standard.get(
                    "standard_name"
                )

                if number and name:

                    lines.append(
                        f"- **{number}** — {name}"
                    )

                elif number:

                    lines.append(
                        f"- **{number}**"
                    )

                elif name:

                    lines.append(
                        f"- {name}"
                    )

        else:

            lines.append(
                "- No matching record was returned by the official BIS live search."
            )

        lines.extend([
            "",
            "## BISathi Product Database",
            ""
        ])

        if local_found:

            lines.append(
                f"- Local product match: **{product_data.get('product', product)}**"
            )

            if product_data.get("standard"):

                lines.append(
                    f"- Local standard: **{product_data.get('standard')}**"
                )

            if product_data.get("standard_title"):

                lines.append(
                    f"- Standard title: {product_data.get('standard_title')}"
                )

            if product_data.get("certification"):

                lines.append(
                    f"- Local certification guidance: {product_data.get('certification')}"
                )

        else:

            lines.append(
                "- No matching product record was found in BISathi's local JSON database."
            )

        lines.extend([
            "",
            "## What This Means",
            "",
            "- The official BIS search result is the primary source for the standards shown above.",
            "- A standard search result alone does not prove that a particular product carries a valid BIS licence or ISI mark.",
            "- Licence / CM/L details should be verified through the appropriate official BIS verification facility.",
            "",
            "## Important",
            "",
            "BISathi provides preliminary verification guidance in this prototype. It should not be treated as a certificate or licence authenticity determination."
        ])

        answer = "\n".join(lines)

    return {
        "verification_status": verification_status,
        "official_bis_found": live_found,
        "local_product_found": local_found,
        "answer": answer
    }


def build_isi_verification(
    product_data,
    user_type
):

    p_name = product_data.get(
        "product",
        "your product"
    )

    std = product_data.get(
        "standard",
        ""
    )

    title = product_data.get(
        "standard_title",
        ""
    )

    cert = product_data.get(
        "certification",
        ""
    )

    verif = product_data.get(
        "verification",
        ""
    )

    is_consumer = user_type not in [
        "industry",
        "manufacturer"
    ]

    lines = [
        "## ISI Mark Verification Guidance",
        "",
        f"Guidance for checking BIS / ISI info for **{p_name}**.",
        ""
    ]

    if is_consumer:

        lines.extend([
            "## What Consumers Should Check",
            "",
            "- Look for BIS / ISI marking info on the product or packaging.",
            "- Check product name and exact product category.",
            "- Check the relevant Indian Standard number.",
            "- Check manufacturer or brand information.",
            "- Check licence/certification number (CM/L).",
            "- Compare details with official BIS resources (BIS CARE App).",
            "- Be cautious if marking is incomplete or unclear."
        ])

    else:

        lines.extend([
            "## For Industry / Manufacturers",
            "",
            "- Identify the exact Indian Standard applicable to the product.",
            "- Determine applicable BIS certification or marking mandates.",
            "- Check conformity-assessment, testing, and certification procedures.",
            "- Ensure product marking strictly adheres to BIS guidelines.",
            "- Verify current requirements through official BIS sources."
        ])

    lines.extend([
        "",
        "## Product Standard",
        ""
    ])

    lines.append(
        f"- {std}: {title}"
        if std and title
        else f"- {std}"
        if std
        else "- The applicable Indian Standard must be determined for the exact product."
    )

    lines.extend([
        "",
        "## Certification Information",
        "",
        f"- {cert}"
        if cert
        else "- Check whether BIS certification applies to this exact product."
    ])

    if verif:

        lines.extend([
            "",
            "## BISathi Verification Note",
            "",
            verif
        ])

    lines.extend([
        "",
        "## Important",
        "",
        "BISathi provides preliminary guidance. It does not perform live BIS certificate verification in this prototype.",
        "Check official BIS portals to verify licence numbers and details."
    ])

    return "\n".join(
        lines
    )


# ============================================================
# LOCAL BIS ANSWERS
# ============================================================

def get_local_bis_answer(
    question,
    user_type
):

    q_low = question.lower().strip()

    k_item = find_bis_knowledge(
        question
    )

    if k_item:

        ans = build_bis_knowledge_response(
            k_item,
            user_type
        )

        if ans:

            return {
                "answer": ans,
                "source_type": get_knowledge_source_type(
                    k_item,
                    user_type
                )
            }

    is_ind = user_type in [
        "industry",
        "manufacturer"
    ]

    if any(
        k in q_low
        for k in [
            "bis certificate",
            "bis certification",
            "how to get bis",
            "how does bis certification work"
        ]
    ):

        ans = (
            "## BIS Certification\n\n"
            "Conformity-assessment mechanism for products under applicable Indian Standards.\n\n"
            "## General Process\n\n"
            "- Identify Indian Standard.\n"
            "- Determine regulatory requirement.\n"
            "- Review documentation.\n"
            "- Complete testing.\n"
            "- Apply for licence.\n\n"
            "## Important\n\n"
            "Exact process depends on the product. Verify via official BIS sources."
            if is_ind
            else
            "## BIS Certificate\n\n"
            "Certification issued under BIS conformity assessment.\n\n"
            "## What Consumers Should Know\n\n"
            "- Requirements differ by product.\n"
            "- Look for standard BIS/ISI mark.\n"
            "- Verify licence via official BIS tools.\n\n"
            "## Important\n\n"
            "Check official sources to see if certification is mandatory for the product."
        )

        return {
            "answer": ans,
            "source_type": "certification"
        }

    if any(
        k in q_low
        for k in [
            "certification process",
            "certification procedure",
            "bis process",
            "bis procedure"
        ]
    ):

        return {
            "answer": (
                "## BIS Certification Process\n\n"
                "- Identify product and applicable Standard.\n"
                "- Check mandatory/voluntary status.\n"
                "- Review testing requirements.\n"
                "- Submit application on portal.\n"
                "- Inspection and licence grant.\n\n"
                "## Important\n\n"
                "Verify exact steps on the official BIS portal."
            ),
            "source_type": "certification"
        }

    if any(
        k in q_low
        for k in [
            "bis documents",
            "documents for bis",
            "documents required for bis",
            "what documents"
        ]
    ):

        return {
            "answer": (
                "## BIS Documents\n\n"
                "## Common Requirements\n\n"
                "- Factory registration/business proof.\n"
                "- Manufacturing process flow.\n"
                "- In-house testing machinery list.\n"
                "- Calibration certificates.\n"
                "- Test reports from recognized labs.\n\n"
                "## Important\n\n"
                "Exact documents depend on the applicable scheme."
            ),
            "source_type": "documents"
        }

    if any(
        k in q_low
        for k in [
            "what is an indian standard",
            "what are indian standards",
            "what is indian standard"
        ]
    ):

        return {
            "answer": (
                "## Indian Standards\n\n"
                "Standards formulated by BIS establishing specifications for quality, safety, and performance.\n\n"
                "## Key Objectives\n\n"
                "- Ensure product safety and reliability.\n"
                "- Standardize manufacturing practices.\n"
                "- Facilitate trade and consumer protection."
            ),
            "source_type": "standards"
        }

    if any(
        k in q_low
        for k in [
            "isi mark",
            "isi mark meaning",
            "what is isi",
            "how to verify isi",
            "verify isi mark"
        ]
    ):

        ans = (
            "## ISI Mark\n\n"
            "Mark of conformity for products compliant with Indian Standards.\n\n"
            "## For Manufacturers\n\n"
            "- Identify standard and testing requirements.\n"
            "- Obtain licence prior to using mark.\n\n"
            "## Important\n\n"
            "Verify QCOs to check mandatory status."
            if is_ind
            else
            "## ISI Mark\n\n"
            "Quality and safety certification mark on consumer goods.\n\n"
            "## Verification Tips\n\n"
            "- Check for the IS number above mark and 7-digit CM/L number below.\n"
            "- Verify on BIS CARE App.\n\n"
            "## Important\n\n"
            "Ensure mark details are genuine and clear."
        )

        return {
            "answer": ans,
            "source_type": "isi"
        }

    if q_low in [
        "bis",
        "what is bis",
        "what's bis",
        "what is the bis",
        "what is bureau of indian standards",
        "what is the bureau of indian standards"
    ]:

        return {
            "answer": (
                "## What is BIS?\n\n"
                "Bureau of Indian Standards is India's National Standard Body responsible for the harmonious development of standardization, marking, and quality certification."
            ),
            "source_type": "general"
        }

    if any(
        k in q_low
        for k in [
            "bis services",
            "what services does bis provide",
            "services of bis"
        ]
    ):

        return {
            "answer": (
                "## BIS Services\n\n"
                "- Standards formulation.\n"
                "- Product certification (ISI Mark).\n"
                "- Compulsory Registration Scheme (CRS) for electronics.\n"
                "- Hallmarking of gold/silver.\n"
                "- Laboratory services and testing."
            ),
            "source_type": "general"
        }

    p_data = find_product(
        question
    )

    if p_data:

        return {
            "answer": build_product_response(
                p_data,
                user_type
            ),
            "source_type": "standards"
        }

    return None


# ============================================================
# GENERAL AI FALLBACK
# ============================================================

def build_ai_fallback(
    question,
    user_type,
    reason="general"
):

    q_low = question.lower().strip()

    if any(
        k in q_low
        for k in [
            "certification",
            "certificate",
            "license",
            "licence"
        ]
    ):

        return (
            "## BIS Certification Guidance\n\n"
            "AI service is temporarily unavailable.\n\n"
            "- Identify product and applicable Indian Standard.\n"
            "- Check QCOs for mandatory applicability.\n"
            "- Prepare technical documentation and complete testing.\n"
            "- Apply via official BIS portal."
        )

    if any(
        k in q_low
        for k in [
            "isi",
            "mark"
        ]
    ):

        return (
            "## ISI Mark Guidance\n\n"
            "AI service is temporarily unavailable.\n\n"
            "- Check IS number above and CM/L number below mark.\n"
            "- Verify details via BIS CARE App.\n"
            "- Ensure packaging details match official records."
        )

    if any(
        k in q_low
        for k in [
            "standard",
            "indian standard"
        ]
    ):

        return (
            "## Indian Standards\n\n"
            "AI service is temporarily unavailable.\n\n"
            "Use the Standards search feature to look up supported products or consult the official BIS Know Your Standards portal."
        )

    if any(
        k in q_low
        for k in [
            "document",
            "documents",
            "paperwork"
        ]
    ):

        return (
            "## BIS Document Guidance\n\n"
            "AI service is temporarily unavailable.\n\n"
            "Common docs: Factory registration, machinery list, test equipment records, calibration certificates, and raw material details."
        )

    return (
        "## BISathi Assistant\n\n"
        "AI service is temporarily unavailable. "
        "Use standard features to search products, "
        "verify ISI marks, and explore local checklists."
    )


# ============================================================
# GEMINI PROMPTS
# ============================================================

SYSTEM_PROMPT = """You are BISathi, an AI-powered assistant for Indian Standards and BIS services.
Adapt explanations for Consumers (simple, practical) or Industry/Manufacturers (process, compliance, testing).
Never invent standard numbers or mandatory certifications. Always emphasize verifying through official BIS portals.
Format using clean Markdown (## headings, - bullets, sequential numbered steps when needed)."""


SEARCH_PROMPT = """You are BISathi's Indian Standards discovery assistant.
Provide preliminary guidance for a product not found in the local database.
Format strictly with these sections:
## Product
## Relevant BIS / Indian Standard Guidance
## Certification / Compliance
## What to Check
## Important
Do not invent standard numbers or certification requirements. Use '-' for bullets."""


# ============================================================
# CERTIFICATION GUIDE GEMINI PROMPT
# ============================================================

CERTIFICATION_GEMINI_PROMPT = """You are BISathi's Certification Guide assistant.

The user has asked about BIS certification for a specific product.

The official BIS Know Your Standards service has already been searched.
The BIS search results supplied below are the PRIMARY factual grounding.

Your job is to explain the certification-related guidance in simple,
practical language.

IMPORTANT RULES:

1. Use the supplied official BIS live search results as the primary
   source for Indian Standard numbers and titles.

2. Do NOT invent an Indian Standard number.

3. Do NOT say that BIS certification is mandatory merely because an
   Indian Standard exists.

4. Do NOT invent a Quality Control Order (QCO).

5. Do NOT invent licence numbers, CM/L numbers, certificate numbers,
   fees, testing laboratories, or application requirements.

6. If mandatory certification cannot be established from the supplied
   information, clearly state that current BIS requirements and
   applicable QCOs must be checked through official BIS sources.

7. Explain the difference between:
   - an Indian Standard existing for a product
   - BIS certification/licensing
   - mandatory certification requirements

8. Adapt the answer for the user type:
   - Consumer: simple and practical.
   - Industry/Manufacturer: process, documentation, testing and
     certification considerations.

9. Do not claim that you independently verified anything outside the
   supplied BIS records.

10. The answer is guidance only and should direct the user to official
    BIS sources for final certification decisions.

Use exactly these sections:

## BIS Certification Guidance

## Official BIS Standards Found

## Certification / Compliance

## Recommended Path

## Important

Use clean Markdown and '-' bullets.
"""


def build_certification_gemini_prompt(
    product,
    user_type,
    question,
    standards
):

    if standards:

        records = []

        for standard in standards:

            records.append(
                "\n".join([
                    f"Standard Number: {standard.get('standard_number', '')}",
                    f"Standard Name: {standard.get('standard_name', '')}",
                    f"Published On: {standard.get('published_on', '')}",
                    f"Valid Upto: {standard.get('valid_upto', '')}",
                    f"Withdraw Status: {standard.get('withdraw_status', '')}",
                    f"Withdraw On: {standard.get('withdraw_on', '')}",
                    f"Status: {standard.get('status', '')}"
                ])
            )

        bis_context = "\n\n".join(
            records
        )

    else:

        bis_context = (
            "No matching records were returned by "
            "the official BIS live search."
        )

    return (
        f"{CERTIFICATION_GEMINI_PROMPT}\n\n"
        f"USER TYPE:\n{user_type}\n\n"
        f"USER QUESTION:\n{question}\n\n"
        f"PRODUCT:\n{product}\n\n"
        f"OFFICIAL BIS LIVE SEARCH RESULTS:\n\n"
        f"{bis_context}"
    )


# ============================================================
# CERTIFICATION GUIDE LOCAL JSON ADDITION
# ============================================================

def build_certification_local_json_section(
    product_data,
    user_type
):

    if not product_data:

        return (
            "## BISathi Local Product Guidance\n\n"
            "- No matching product was found in BISathi's local products.json database."
        )

    p_name = product_data.get(
        "product",
        "your product"
    )

    std = product_data.get(
        "standard",
        ""
    )

    title = product_data.get(
        "standard_title",
        ""
    )

    cert = product_data.get(
        "certification",
        ""
    )

    verification = product_data.get(
        "verification",
        ""
    )

    if user_type in [
        "industry",
        "manufacturer"
    ]:

        checks = product_data.get(
            "industry_guidance",
            []
        )

    else:

        checks = product_data.get(
            "consumer_checks",
            []
        )

    lines = [
        "## BISathi Local Product Guidance",
        "",
        f"- Product: **{p_name}**"
    ]

    if std:

        lines.append(
            (
                f"- Local Indian Standard: **{std}**"
                + (
                    f" — {title}"
                    if title
                    else ""
                )
            )
        )

    if cert:

        lines.extend([
            "",
            "### Local Certification Guidance",
            "",
            f"- {cert}"
        ])

    if checks:

        lines.extend([
            "",
            "### Local Product Checks",
            ""
        ])

        for item in checks:

            if item:

                lines.append(
                    f"- {item}"
                )

    if verification:

        lines.extend([
            "",
            "### Local Verification Note",
            "",
            f"- {verification}"
        ])

    return "\n".join(
        lines
    )


def build_certification_fallback(
    product,
    user_type,
    standards,
    product_data
):

    live_answer = build_live_bis_standard_response(
        standards,
        product,
        user_type
    )

    local_section = build_certification_local_json_section(
        product_data,
        user_type
    )

    return (
        live_answer
        + "\n\n"
        + local_section
        + "\n\n"
        + "## Certification Guidance"
        + "\n\n"
        + "- The official BIS search results identify relevant standards for the entered product."
        + "\n- The existence of a standard does not by itself establish mandatory BIS certification."
        + "\n- Check current BIS requirements and applicable QCOs before making a certification decision."
        + "\n- Use the official BIS certification process and licensing resources for the final procedure."
    )


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="BISathi API",
    description="AI-powered assistant for Indian Standards and BIS services",
    version="2.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODELS
# ============================================================

class QuestionRequest(BaseModel):

    question: str
    user_type: str = "consumer"


class ProductSearchRequest(BaseModel):

    product: str
    user_type: str = "consumer"


class CertificationRequest(BaseModel):

    product: str
    user_type: str = "manufacturer"


class DocumentChecklistRequest(BaseModel):

    product: str
    user_type: str = "manufacturer"


class ISIVerificationRequest(BaseModel):

    product: str
    user_type: str = "consumer"


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "status": "online",
        "application": "BISathi",
        "message": "BISathi API is running"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "ai_configured": client is not None,
        "product_database": os.path.exists(
            PRODUCTS_FILE
        ),
        "bis_knowledge_base": os.path.exists(
            BIS_KNOWLEDGE_FILE
        ),
        "live_bis_standards_service": True,
    }


# ============================================================
# MAIN BISATHI ASSISTANT
# ============================================================

@app.post("/api/ask")
def ask_bis_ai(
    request: QuestionRequest
):

    question = request.question.strip()

    user_type = (
        request.user_type
        .strip()
        .lower()
    )

    if user_type not in [
        "consumer",
        "industry",
        "manufacturer"
    ]:

        user_type = "consumer"

    if not question:

        return {
            "success": False,
            "answer": "Please enter a question.",
            "sources": []
        }

    if is_product_compliance_question(
        question
    ):

        product_query = (
            extract_product_from_question(
                question
            )
        )

        print(
            f"[BISathi] Compliance question detected: "
            f"{question}"
        )

        print(
            f"[BISathi] Extracted product: "
            f"{product_query}"
        )

        live_result = None

        if product_query:

            try:

                live_result = search_bis_standards(
                    product_query
                )

            except Exception as e:

                print(
                    f"[BISathi] Live BIS search error: {e}"
                )

                live_result = {
                    "success": False,
                    "standards": [],
                    "total_records": 0,
                    "message": str(e)
                }

        live_standards = []

        if live_result:

            live_standards = (
                live_result.get(
                    "standards",
                    []
                )
                if live_result.get(
                    "success"
                )
                else []
            )

        if live_standards:

            print(
                f"[BISathi] Official BIS found "
                f"{len(live_standards)} record(s)."
            )

            product_data = (
                find_product(
                    product_query
                )
                if product_query
                else None
            )

            if client is not None:

                try:

                    grounded_prompt = (
                        build_gemini_compliance_prompt(
                            question=question,
                            product=product_query,
                            user_type=user_type,
                            standards=live_standards
                        )
                    )

                    response = (
                        client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=grounded_prompt
                        )
                    )

                    if (
                        response.text
                        and response.text.strip()
                    ):

                        sources = get_official_sources(
                            "standards"
                        )

                        return {
                            "success": True,
                            "product": product_query,
                            "matched_product": product_query,
                            "source": "official_bis_live_search_and_gemini",
                            "answer": clean_product_response(
                                response.text
                            ),
                            "total_records": live_result.get(
                                "total_records",
                                len(live_standards)
                            ),
                            "standards": live_standards,
                            "sources": sources,
                            "official_sources": sources,
                        }

                    raise Exception(
                        "Gemini returned empty response."
                    )

                except Exception as e:

                    print(
                        f"[BISathi] Gemini compliance "
                        f"response failed: {e}"
                    )

            sources = get_official_sources(
                "standards"
            )

            return {
                "success": True,
                "product": product_query,
                "matched_product": (
                    product_data.get(
                        "product",
                        product_query
                    )
                    if product_data
                    else product_query
                ),
                "source": (
                    "official_bis_live_search_and_local_data"
                    if product_data
                    else "official_bis_live_search_fallback"
                ),
                "answer": build_live_compliance_fallback(
                    standards=live_standards,
                    product=product_query,
                    user_type=user_type,
                    product_data=product_data
                ),
                "total_records": live_result.get(
                    "total_records",
                    len(live_standards)
                ),
                "standards": live_standards,
                "sources": sources,
                "official_sources": sources,
            }

        print(
            "[BISathi] No live BIS records found."
        )

        if client is not None:

            try:

                response = (
                    client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=(
                            f"{SYSTEM_PROMPT}\n\n"
                            f"Important: The official BIS live "
                            f"search did not return a matching "
                            f"record for the product.\n"
                            f"Do not invent BIS standard numbers "
                            f"or mandatory certification claims.\n\n"
                            f"User Type:\n{user_type}\n\n"
                            f"Product:\n{product_query}\n\n"
                            f"User Question:\n{question}\n\n"
                            f"Explain what the user should check "
                            f"and clearly state that exact BIS "
                            f"applicability must be verified "
                            f"through official BIS sources."
                        )
                    )
                )

                if (
                    response.text
                    and response.text.strip()
                ):

                    sources = get_official_sources(
                        "standards"
                    )

                    return {
                        "success": True,
                        "product": product_query,
                        "source": "gemini_after_bis_search",
                        "answer": clean_product_response(
                            response.text
                        ),
                        "total_records": 0,
                        "standards": [],
                        "sources": sources,
                        "official_sources": sources,
                    }

            except Exception as e:

                print(
                    f"[BISathi] Gemini fallback failed: {e}"
                )

        product_data = (
            find_product(
                product_query
            )
            if product_query
            else None
        )

        if product_data:

            sources = get_official_sources(
                "standards"
            )

            return {
                "success": True,
                "product": product_query,
                "matched_product": product_data.get(
                    "product",
                    product_query
                ),
                "source": "local_products_json_fallback",
                "answer": build_product_response(
                    product_data,
                    user_type
                ),
                "total_records": 0,
                "standards": [],
                "sources": sources,
                "official_sources": sources,
            }

        sources = get_official_sources(
            "standards"
        )

        return {
            "success": True,
            "product": product_query,
            "source": "local_fallback",
            "answer": build_ai_fallback(
                question,
                user_type,
                "not_found"
            ),
            "total_records": 0,
            "standards": [],
            "sources": sources,
            "official_sources": sources,
        }

    local_result = get_local_bis_answer(
        question,
        user_type
    )

    if local_result:

        sources = get_official_sources(
            local_result.get(
                "source_type",
                "general"
            )
        )

        return {
            "success": True,
            "answer": local_result["answer"],
            "source": "local_knowledge_base",
            "sources": sources,
            "official_sources": sources,
        }

    if client is None:

        sources = get_official_sources()

        return {
            "success": True,
            "answer": build_ai_fallback(
                question,
                user_type,
                "not_configured"
            ),
            "source": "local_fallback",
            "sources": sources,
            "official_sources": sources,
        }

    try:

        response = (
            client.models.generate_content(
                model="gemini-3.8-flash",
                contents=(
                    f"{SYSTEM_PROMPT}\n\n"
                    f"User Type:\n{user_type}\n\n"
                    f"User Question:\n{question}"
                ),
            )
        )

        if (
            not response.text
            or not response.text.strip()
        ):

            raise Exception(
                "Gemini returned empty response."
            )

        sources = get_official_sources()

        return {
            "success": True,
            "answer": response.text,
            "source": "gemini",
            "sources": sources,
            "official_sources": sources
        }

    except Exception as e:

        reason = (
            "quota"
            if any(
                x in str(e)
                for x in [
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "quota"
                ]
            )
            else "error"
        )

        sources = get_official_sources()

        return {
            "success": True,
            "answer": build_ai_fallback(
                question,
                user_type,
                reason
            ),
            "source": "local_fallback",
            "sources": sources,
            "official_sources": sources,
        }


# ============================================================
# STANDARD SEARCH
# ============================================================

@app.post("/api/search-standard")
def search_standard(
    request: ProductSearchRequest
):

    product = request.product.strip()

    user_type = (
        request.user_type
        .strip()
        .lower()
    )

    if user_type not in [
        "consumer",
        "industry",
        "manufacturer"
    ]:

        user_type = "consumer"

    if not product:

        return {
            "success": False,
            "answer": "Please enter a product name.",
            "sources": get_official_sources(
                "standards"
            )
        }

    live_result = search_bis_standards(
        product
    )

    if (
        live_result.get("success")
        and live_result.get("standards")
    ):

        sources = get_official_sources(
            "standards"
        )

        return {
            "success": True,
            "product": product,
            "matched_product": product,
            "source": "official_bis_live_search",
            "answer": build_live_bis_standard_response(
                live_result["standards"],
                product,
                user_type
            ),
            "total_records": live_result.get(
                "total_records",
                len(
                    live_result["standards"]
                )
            ),
            "standards": live_result[
                "standards"
            ],
            "sources": sources,
            "official_sources": sources,
        }

    product_data = find_product(
        product
    )

    if product_data:

        sources = get_official_sources(
            "standards"
        )

        return {
            "success": True,
            "product": product,
            "matched_product": product_data.get(
                "product",
                product
            ),
            "source": "local_knowledge_base",
            "answer": build_product_response(
                product_data,
                user_type
            ),
            "sources": sources,
            "official_sources": sources,
        }

    if client is None:

        return {
            "success": False,
            "answer": (
                "BISathi could not find live BIS results "
                "for this product, and the AI service "
                "is not configured."
            ),
            "source": "not_found",
            "sources": get_official_sources(
                "standards"
            ),
        }

    max_attempts = 3

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            response = (
                client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=(
                        f"{SEARCH_PROMPT}\n\n"
                        f"User Type:\n{user_type}\n\n"
                        f"Product:\n{product}"
                    ),
                )
            )

            sources = get_official_sources(
                "standards"
            )

            return {
                "success": True,
                "product": product,
                "source": "ai",
                "answer": clean_product_response(
                    response.text
                ),
                "sources": sources,
                "official_sources": sources,
            }

        except Exception as e:

            err = str(e)

            if any(
                x in err
                for x in [
                    "429",
                    "RESOURCE_EXHAUSTED",
                    "quota"
                ]
            ):

                return {
                    "success": False,
                    "answer": (
                        "Product not found in live search, "
                        "and AI request quota was reached."
                    ),
                    "source": "quota_fallback",
                    "sources": get_official_sources(
                        "standards"
                    ),
                }

            if (
                (
                    "503" in err
                    or "UNAVAILABLE" in err
                )
                and attempt < max_attempts
            ):

                time.sleep(
                    attempt * 2
                )

                continue

            break

    return {
        "success": False,
        "answer": (
            "BISathi could not find this product "
            "in BIS records, and the AI service "
            "is temporarily unavailable."
        ),
        "source": "search_failed",
        "sources": get_official_sources(
            "standards"
        ),
    }


# ============================================================
# CERTIFICATION GUIDE
#
# USER QUESTION
#      ↓
# OFFICIAL BIS LIVE SEARCH
#      ↓
# GEMINI INTERPRETATION
#      ↓
# LOCAL products.json CROSS-CHECK
#      ↓
# FINAL CERTIFICATION GUIDANCE
# ============================================================

@app.post("/api/certification-guide")
def certification_guide(
    request: CertificationRequest
):

    product = request.product.strip()

    user_type = (
        request.user_type
        .strip()
        .lower()
    )

    if user_type not in [
        "consumer",
        "industry",
        "manufacturer"
    ]:

        user_type = "manufacturer"

    if not product:

        return {
            "success": False,
            "answer": "Please enter a product name.",
            "certification_status": "INPUT_REQUIRED",
            "official_bis_found": False,
            "local_product_found": False,
            "gemini_status": "not_used",
            "standards": [],
            "sources": get_official_sources(
                "certification"
            ),
            "official_sources": get_official_sources(
                "certification"
            )
        }

    # ========================================================
    # STEP 1
    # OFFICIAL BIS LIVE SEARCH
    # ========================================================

    print(
        f"[BISathi] Certification Guide started: {product}"
    )

    live_result = None

    try:

        live_result = search_bis_standards(
            product
        )

        print(
            "[BISathi] Certification Guide BIS search completed."
        )

    except Exception as e:

        print(
            f"[BISathi] Certification Guide BIS search error: {e}"
        )

        live_result = {
            "success": False,
            "message": str(e),
            "total_records": 0,
            "standards": []
        }

    live_standards = []

    if (
        live_result
        and live_result.get("success")
    ):

        live_standards = (
            live_result.get(
                "standards",
                []
            )
        )

    print(
        f"[BISathi] Certification Guide official BIS records: "
        f"{len(live_standards)}"
    )

    # ========================================================
    # STEP 2
    # GEMINI ANALYSIS OF OFFICIAL BIS RESULTS
    # ========================================================

    gemini_answer = None
    gemini_status = "not_used"

    if client is not None:

        try:

            grounded_prompt = (
                build_certification_gemini_prompt(
                    product=product,
                    user_type=user_type,
                    question=(
                        f"Provide BIS certification guidance "
                        f"for {product}."
                    ),
                    standards=live_standards
                )
            )

            print(
                "[BISathi] Sending official BIS results to Gemini..."
            )

            response = (
                client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=grounded_prompt
                )
            )

            if (
                response.text
                and response.text.strip()
            ):

                gemini_answer = response.text.strip()

                gemini_status = "success"

                print(
                    "[BISathi] Gemini Certification Guide analysis completed."
                )

            else:

                gemini_status = "empty_response"

        except Exception as e:

            error_text = str(e)

            gemini_status = (
                "quota"
                if any(
                    value in error_text
                    for value in [
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "quota"
                    ]
                )
                else "error"
            )

            print(
                f"[BISathi] Gemini Certification Guide failed: "
                f"{error_text}"
            )

    else:

        gemini_status = "not_configured"

    # ========================================================
    # STEP 3
    # LOCAL products.json CROSS-CHECK
    # ========================================================

    product_data = find_product(
        product
    )

    if product_data:

        print(
            "[BISathi] Certification Guide local JSON match found: "
            f"{product_data.get('product', product)}"
        )

    else:

        print(
            "[BISathi] Certification Guide local JSON match not found."
        )

    # ========================================================
    # STEP 4
    # BUILD FINAL RESPONSE
    # ========================================================

    sources = get_official_sources(
        "certification"
    )

    official_bis_found = bool(
        live_standards
    )

    local_product_found = bool(
        product_data
    )

    # --------------------------------------------------------
    # GEMINI AVAILABLE
    # --------------------------------------------------------

    if gemini_answer:

        answer = clean_product_response(
            gemini_answer
        )

        # Add local JSON only after Gemini has interpreted
        # the official BIS search results.
        answer = (
            answer
            + "\n\n"
            + build_certification_local_json_section(
                product_data=product_data,
                user_type=user_type
            )
            + "\n\n"
            + "## Final Verification Note"
            + "\n\n"
            + "- Official BIS live search was used as the primary source."
            + "\n- Gemini was used to interpret the retrieved BIS information."
            + "\n- BISathi local products.json was used as supplementary product guidance."
            + "\n- Final certification applicability should be confirmed through official BIS requirements and applicable QCOs."
        )

        source = (
            "official_bis_live_search_gemini_local_json"
        )

    # --------------------------------------------------------
    # GEMINI UNAVAILABLE
    # --------------------------------------------------------

    else:

        answer = build_certification_fallback(
            product=product,
            user_type=user_type,
            standards=live_standards,
            product_data=product_data
        )

        if live_standards and product_data:

            source = (
                "official_bis_live_search_local_json"
            )

        elif live_standards:

            source = (
                "official_bis_live_search_fallback"
            )

        elif product_data:

            source = (
                "local_json_after_bis_search"
            )

        else:

            source = (
                "bis_search_no_match"
            )

    # ========================================================
    # CERTIFICATION STATUS
    # ========================================================

    if (
        official_bis_found
        and local_product_found
    ):

        certification_status = (
            "BIS STANDARD FOUND + LOCAL PRODUCT MATCH"
        )

    elif official_bis_found:

        certification_status = (
            "BIS STANDARD FOUND + LOCAL PRODUCT NOT FOUND"
        )

    elif local_product_found:

        certification_status = (
            "LOCAL PRODUCT MATCH + BIS LIVE RESULT NOT FOUND"
        )

    else:

        certification_status = (
            "NO BIS OR LOCAL PRODUCT RECORD FOUND"
        )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {
        "success": True,

        "product": product,

        "matched_product": (
            product_data.get(
                "product",
                product
            )
            if product_data
            else product
        ),

        "source": source,

        "certification_status": certification_status,

        "official_bis_found": official_bis_found,

        "local_product_found": local_product_found,

        "gemini_status": gemini_status,

        "answer": answer,

        "total_records": (
            live_result.get(
                "total_records",
                len(live_standards)
            )
            if live_result
            else 0
        ),

        "standards": live_standards,

        "local_product": (
            product_data
            if product_data
            else None
        ),

        "sources": sources,

        "official_sources": sources,
    }


# ============================================================
# DOCUMENT CHECKLIST
#
# OFFICIAL BIS
#      ↓
# LOCAL PRODUCT DATA
#      ↓
# CHECKLIST
# ============================================================

@app.post("/api/document-checklist")
def document_checklist(
    request: DocumentChecklistRequest
):

    product = request.product.strip()

    user_type = (
        request.user_type
        .strip()
        .lower()
    )

    if user_type not in [
        "consumer",
        "industry",
        "manufacturer"
    ]:

        user_type = "manufacturer"

    if not product:

        return {
            "success": False,
            "answer": "Please enter a product name.",
            "checklist": [],
            "checklist_total": 0,
            "checklist_completed": 0,
            "sources": get_official_sources(
                "documents"
            )
        }

    print(
        f"[BISathi] Document checklist search: {product}"
    )

    live_result = None

    try:

        live_result = search_bis_standards(
            product
        )

    except Exception as e:

        print(
            f"[BISathi] Document checklist BIS error: {e}"
        )

        live_result = {
            "success": False,
            "standards": [],
            "total_records": 0,
            "message": str(e)
        }

    live_standards = []

    if (
        live_result
        and live_result.get("success")
    ):

        live_standards = (
            live_result.get(
                "standards",
                []
            )
        )

    print(
        f"[BISathi] Official BIS records found: "
        f"{len(live_standards)}"
    )

    product_data = find_product(
        product
    )

    if product_data:

        print(
            "[BISathi] Local product data found: "
            f"{product_data.get('product', product)}"
        )

    else:

        print(
            "[BISathi] No local product data found."
        )

    checklist_result = build_document_checklist(
        product_data=product_data,
        user_type=user_type,
        live_standards=live_standards,
        product_name=product
    )

    sources = get_official_sources(
        "documents"
    )

    if live_standards and product_data:

        source = (
            "official_bis_live_search_and_local_product_data"
        )

    elif live_standards:

        source = (
            "official_bis_live_search"
        )

    elif product_data:

        source = (
            "local_product_data"
        )

    else:

        source = (
            "default_bisathi_checklist"
        )

    return {
        "success": True,
        "product": product,
        "matched_product": (
            product_data.get(
                "product",
                product
            )
            if product_data
            else product
        ),

        "source": source,

        "answer": checklist_result[
            "answer"
        ],

        "checklist": checklist_result[
            "checklist"
        ],

        "checklist_total": checklist_result[
            "checklist_total"
        ],

        "checklist_completed": checklist_result[
            "checklist_completed"
        ],

        "checklist_source": checklist_result[
            "checklist_source"
        ],

        "total_records": (
            live_result.get(
                "total_records",
                len(live_standards)
            )
            if live_result
            else 0
        ),

        "standards": live_standards,

        "sources": sources,

        "official_sources": sources,
    }


# ============================================================
# ISI VERIFICATION
#
# USER INPUT
#      ↓
# OFFICIAL BIS LIVE SEARCH
#      ↓
# GEMINI INTERPRETATION
#      ↓
# LOCAL products.json CROSS-CHECK
#      ↓
# FINAL VERIFICATION RESULT
# ============================================================

@app.post("/api/verify-isi")
def verify_isi(
    request: ISIVerificationRequest
):

    product = request.product.strip()

    user_type = (
        request.user_type
        .strip()
        .lower()
    )

    if user_type not in [
        "consumer",
        "industry",
        "manufacturer"
    ]:

        user_type = "consumer"

    if not product:

        return {
            "success": False,
            "answer": "Please enter a product name.",
            "verification_status": "INPUT_REQUIRED",
            "official_bis_found": False,
            "local_product_found": False,
            "standards": [],
            "sources": get_official_sources(
                "isi"
            ),
            "official_sources": get_official_sources(
                "isi"
            )
        }

    print(
        f"[BISathi] ISI verification started: {product}"
    )

    live_result = None

    try:

        live_result = search_bis_standards(
            product
        )

        print(
            "[BISathi] ISI official BIS search completed."
        )

    except Exception as e:

        print(
            f"[BISathi] ISI BIS search error: {e}"
        )

        live_result = {
            "success": False,
            "message": str(e),
            "total_records": 0,
            "standards": []
        }

    live_standards = []

    if (
        live_result
        and live_result.get("success")
    ):

        live_standards = (
            live_result.get(
                "standards",
                []
            )
        )

    print(
        f"[BISathi] ISI official BIS records: "
        f"{len(live_standards)}"
    )

    product_data = find_product(
        product
    )

    if product_data:

        print(
            "[BISathi] ISI local JSON match found: "
            f"{product_data.get('product', product)}"
        )

    else:

        print(
            "[BISathi] ISI local JSON match not found."
        )

    gemini_answer = None
    gemini_status = "not_used"

    if client is not None:

        try:

            grounded_prompt = build_isi_gemini_prompt(
                product=product,
                standards=live_standards,
                product_data=product_data
            )

            print(
                "[BISathi] Sending BIS results to Gemini..."
            )

            response = (
                client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=grounded_prompt
                )
            )

            if (
                response.text
                and response.text.strip()
            ):

                gemini_answer = response.text.strip()

                gemini_status = "success"

                print(
                    "[BISathi] Gemini ISI analysis completed."
                )

            else:

                gemini_status = "empty_response"

        except Exception as e:

            error_text = str(e)

            gemini_status = (
                "quota"
                if any(
                    value in error_text
                    for value in [
                        "429",
                        "RESOURCE_EXHAUSTED",
                        "quota"
                    ]
                )
                else "error"
            )

            print(
                f"[BISathi] Gemini ISI analysis failed: "
                f"{error_text}"
            )

    else:

        gemini_status = "not_configured"

    result = build_isi_verification_result(
        product=product,
        standards=live_standards,
        product_data=product_data,
        gemini_answer=gemini_answer
    )

    sources = get_official_sources(
        "isi"
    )

    return {
        "success": True,

        "product": product,

        "matched_product": (
            product_data.get(
                "product",
                product
            )
            if product_data
            else product
        ),

        "source": (
            "official_bis_live_search_gemini_local_json"
            if gemini_answer
            else "official_bis_live_search_local_json"
        ),

        "verification_status": result[
            "verification_status"
        ],

        "official_bis_found": result[
            "official_bis_found"
        ],

        "local_product_found": result[
            "local_product_found"
        ],

        "gemini_status": gemini_status,

        "answer": result[
            "answer"
        ],

        "total_records": (
            live_result.get(
                "total_records",
                len(live_standards)
            )
            if live_result
            else 0
        ),

        "standards": live_standards,

        "local_product": (
            product_data
            if product_data
            else None
        ),

        "sources": sources,

        "official_sources": sources,
    }


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )