import requests


BIS_SEARCH_URL = (
    "https://standardsadmin.bis.gov.in/"
    "review-service/searchKnowStandards"
)


def repair_mojibake(text):
    """
    Repair common mojibake characters returned by the BIS service.

    BIS currently returns some UTF-8 punctuation incorrectly decoded.

    Examples:
        â€”  -> —
        â€“  -> –
        â€¦  -> …
        â€œ  -> “
        â€  -> ”
    """

    if not isinstance(text, str):
        return text

    replacements = {
        # Em dash / en dash
        "â€”": "—",
        "â€“": "–",

        # Quotation marks
        "â€œ": "“",
        "â€": "”",
        "â€˜": "‘",
        "â€™": "’",

        # Ellipsis
        "â€¦": "…",

        # Common symbols
        "Â°": "°",
        "Â®": "®",
        "Â©": "©",
        "Â±": "±",
        "Âµ": "µ",
        "Â²": "²",
        "Â³": "³",

        # Non-breaking space
        "Â ": " ",

        # Replacement character where applicable
        "�": ""
    }

    repaired = text

    for corrupted, correct in replacements.items():
        repaired = repaired.replace(
            corrupted,
            correct
        )

    return repaired


def search_bis_standards(search_text: str):
    """
    Search Indian Standards using the official BIS
    Know Your Standards service.
    """

    search_text = search_text.strip()

    if not search_text:
        return {
            "success": False,
            "message": "Search text is required.",
            "total_records": 0,
            "standards": []
        }

    try:
        response = requests.post(
            BIS_SEARCH_URL,
            json={"searchText": search_text},
            timeout=20
        )

        if response.status_code != 200:
            return {
                "success": False,
                "message": (
                    f"BIS service returned "
                    f"HTTP {response.status_code}."
                ),
                "total_records": 0,
                "standards": []
            }

        # Explicitly use UTF-8 for the BIS response.
        response.encoding = "utf-8"

        data = response.json()

        if data.get("status") != "SUCCESS":
            return {
                "success": False,
                "message": data.get(
                    "msg",
                    "BIS search failed."
                ),
                "total_records": 0,
                "standards": []
            }

        standards = []

        for item in data.get("data", []):

            standard_name = repair_mojibake(
                item.get("standardName")
            )

            standard_name_hindi = repair_mojibake(
                item.get("standardNameInHindi")
            )

            matched_standard = repair_mojibake(
                item.get("matched_standard")
            )

            standards.append({
                "standard_id": item.get(
                    "standardId"
                ),

                "standard_number": item.get(
                    "standardNumber"
                ),

                "standard_name": standard_name,

                "standard_name_hindi": standard_name_hindi,

                "department_id": item.get(
                    "departmentId"
                ),

                "committee_id": item.get(
                    "committeeId"
                ),

                "published_on": item.get(
                    "publishedOn"
                ),

                "valid_upto": item.get(
                    "validUpto"
                ),

                "withdraw_status": item.get(
                    "withdrawStatus"
                ),

                "withdraw_on": item.get(
                    "withdrawOn"
                ),

                "status": item.get(
                    "isStatus"
                ),

                "matched_standard": matched_standard
            })

        return {
            "success": True,

            "message": repair_mojibake(
                data.get(
                    "msg",
                    "Standards fetched successfully."
                )
            ),

            "total_records": data.get(
                "totalRecords",
                len(standards)
            ),

            "standards": standards
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "BIS service request timed out.",
            "total_records": 0,
            "standards": []
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": (
                f"Could not connect to BIS: {str(e)}"
            ),
            "total_records": 0,
            "standards": []
        }

    except ValueError:
        return {
            "success": False,
            "message": "BIS returned an invalid response.",
            "total_records": 0,
            "standards": []
        }

    except Exception as e:
        return {
            "success": False,
            "message": (
                f"Unexpected error: {str(e)}"
            ),
            "total_records": 0,
            "standards": []
        }


if __name__ == "__main__":

    result = search_bis_standards(
        "electric iron"
    )

    print(
        "Success:",
        result["success"]
    )

    print(
        "Message:",
        result["message"]
    )

    print(
        "Total records:",
        result["total_records"]
    )

    for standard in result["standards"]:

        print(
            standard["standard_number"],
            "-",
            standard["standard_name"]
        )