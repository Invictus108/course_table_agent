# filtering can be applied to course code, department, professor rating, difficulty, time (prevent collisions)

# mcp_logic.py
from typing import Any, Dict, List
from mcp.server.fastmcp import Context, FastMCP
import random


def create_mcp(data: List[Dict[str, Any]]) -> FastMCP:
    """
    Factory function.
    The caller provides the dataset.
    """
    mcp = FastMCP(name="InMemoryFilterSelect", json_response=True)

    DATA_BY_ID = {}

    for course in data:
        listings = course.get("listings", [])

        for listing in listings:
            crn = listing.get("crn")
            if crn is None:
                continue

            DATA_BY_ID[str(crn)] = {
                # course-level fields
                "crn": crn,
                "title": course.get("title"),
                "average_workload": course.get("average_workload"),
                "average_rating": course.get("average_rating"),
                "description": course.get("description"),
                "areas": course.get("areas"),
                "course_id": course.get("course_id"),
                "course_meetings": course.get("course_meetings"),

                # listing-level fields
                "subject": listing.get("subject"),
                "course_code": listing.get("course_code"),
            }

    # Per-client selected list (in-memory, per process)
    SELECTED: Dict[str, set[str]] = {}

    def selected_set(client_id: str) -> set[str]:
        key = client_id
        if key not in SELECTED:
            SELECTED[key] = set()
        return SELECTED[key]

    # ---- TOOLS ----

    @mcp.tool()
    def query_items(filters: Dict[str, Any], ctx) -> Dict[str, Any]:
        """
        Filter parameters for course search.

        Will return a random sammple of 25 times that match the filters.

        Allowed filters (all optional):

        - course_code:
            Range filter on the numeric portion of the course code.
            Example:
                course_code = [1000, 8000]   # matches courses 1000-8000

        - department:
            One or more department codes (strings).
            Matches courses in ANY of the listed departments.
            Example:
                department = ["CS", "MATH"]
            
            Departments: {'CSSM', 'SNHL', 'ARBC', 'MMES', 'EP&E', 'HPM', 'PLSH', 'MGRK', 'WLOF', 'ELP', 'USAF', 'HEBR', 'HNDI', 'SBCR', 'PHAR', 'AKKD', 'CSMC', 'PMAE', 'PHIL', 'SWED', 'MCDB', 'SMTC', 'ENRG', 'BNGL', 'FLPN', 'OTTM', 'COSM', 'SBS', 'EGYP', 'TAML', 'FNSH', 'BENG', 'CENG', 'EMPH', 'MEDR', 'TLGU', 'ITAL', 'CPSC', 'CZEC', 'PHYS', 'PA', 'RSEE', 'ASL', 'JDST', 'ECE', 'MD', 'EHS', 'CSSY', 'VAIR', 'CSBR', 'CSBF', 'ER&M', 'PUBH', 'CDE', 'HSAR', 'CB&B', 'ENV', 'KREN', 'B&BS', 'MRES', 'MGMT', 'BIS', 'HSCI', 'TDPS', 'HIST', 'SOCY', 'MHHR', 'MEDC', 'ENGL', 'GMAN', 'EDST', 'PHUM', 'BURM', 'CAND', 'GENE', 'MGT', 'EXCH', 'MBIO', 'MUSI', 'PTB', 'HELN', 'CSEC', 'MATH', 'S&DS', 'PERS', 'CSDC', 'CGSC', 'FILM', 'EMD', 'AFAM', 'CLSS', 'UKRN', 'YDSH', 'ENAS', 'IMED', 'RUSS', 'CSJE', 'TBTN', 'HLTH', 'MUS', 'SKRT', 'CSMY', 'AMST', 'PORT', 'REL', 'DISR', 'HSHM', 'INP', 'EALL', 'LAST', 'PRAC', 'DRAM', 'ASTR', 'ART', 'EPS', 'E&RS', 'EVST', 'MENG', 'MDVL', 'PATH', 'CHEM', 'ARCG', 'NURS', 'NAVY', 'CSTC', 'WGSS', 'HGRN', 'VIET', 'ARCH', 'SAST', 'CHNS', 'SWAH', 'CSPC', 'CSGH', 'ACCT', 'MESO', 'PNJB', 'SLAV', 'YORU', 'BIOL', 'NSCI', 'PLSC', 'CLCV', 'ENVE', 'MB&B', 'NELC', 'CSBK', 'APHY', 'ANTH', 'LATN', 'IBIO', 'EEB', 'RLST', 'CSES', 'INDN', 'PSYC', 'FREN', 'LAW', 'SPAN', 'LING', 'NPLI', 'KHMR', 'SCIE', 'CSYC', 'URBN', 'EAST', 'CBIO', 'C&MP', 'GREK', 'TKSH', 'EMST', 'MTBT', 'QUAL', 'AMTH', 'GLBL', 'JAPN', 'AFST', 'ECON', 'ZULU', 'DRST', 'CSTD', 'CHER', 'CPLT', 'DUTC', 'CHLD', 'HUMS'

        - professor_rating:
            Lower bound (inclusive) on professor rating.
            Example:
                professor_rating = 4.2     # rating >= 4.2

        - difficulty:
            Upper bound (inclusive) on course difficulty.
            Example:
                difficulty = 3.5           # difficulty <= 3.5

        - time:
            Range filter on start time (24-hour format).
            Times are integers representing minutes since midnight.
            Example:
                time = [540, 720]           # 9:00–12:00
        
        - keywords
            List of strings (any match).
            Will match words in course title and description.
            Example:
                keywords = ["machine learning", "artificial intelligence"]
        """

        filters = filters or {}
        out = []

        for item in data:
            ok = True

            # course_code: range [min, max]
            if "course_code" in filters:
                lo, hi = filters["course_code"]
                code = item.get("course_code")
                if code != None and len(code.split(" ")) > 1:
                    code = int(code.split(" ")[1].strip()[:4])
                else:
                    code = 0
                if code is None or not (lo <= code <= hi):
                    ok = False

            # department: list of strings (ANY match)
            if ok and "department" in filters:
                dep = item.get("subject")
                if dep != None and dep in filters["department"]:
                    continue
                else:
                    ok = False

            # professor_rating: lower bound
            if ok and "professor_rating" in filters:
                rating = item.get("average_rating", 0)
                if rating == None:
                    rating = 0
                if rating < filters["professor_rating"]:
                    ok = False

            # difficulty: upper bound
            if ok and "difficulty" in filters:
                difficulty = item.get("average_workload", float("inf"))
                if difficulty == None:
                    difficulty = float("inf")
                if difficulty > filters["difficulty"]:
                    ok = False

            # time: range [start, end] (minutes since midnight)
            if ok and "time" in filters:
                start, end = filters["time"]
                t = item.get("time")
                if t is None or not (start <= t <= end):
                    ok = False
            
            if ok and "keywords" in filters:
                for k in filters["keywords"]:
                    if k.lower() in item["title"].lower() or k.lower() in item["description"].lower():
                        break
                else:
                    ok = False

            if ok:
                out.append(item)
        
        # filter out those with same course_id
        clean_out = []
        c_ids = set()
        for i in out:
            if i["course_id"] not in c_ids:
                c_ids.add(i["course_id"])
                clean_out.append(i)
        out = clean_out

        
        random.shuffle(out)

        return {"total": len(out), "items": out[:25]}

    @mcp.tool()
    def add_to_selected(ids: List[str], client_id: str) -> Dict[str, Any]:
        
        """
            Add one or more course IDs to the current user's selected-course list
            (stored in the per-user session context).

            WHEN TO USE:
            - Call this tool when the user explicitly says they want to add/select/save/include
            specific courses in their plan 
            - Only call after you have concrete crns (not just course names).

            ARGUMENTS:
            - ids (List[str]): list of crn codes as strings
            = client_id (str): the users id

            BEHAVIOR:
            - Appends valid IDs to the user's existing selection in ctx.
            - Ignores invalid IDs and IDs already selected (idempotent).
            - Does not remove any previously selected courses.

            RETURNS:
            - Dict with:
            - selected_ids (List[str]): Sorted list of all currently selected course IDs
                after this update.

            DO NOT USE:
            - If the user is only browsing or asking for recommendations without choosing
            specific courses to add.
        """
        sel = selected_set(client_id)
        for i in ids:
            if i in DATA_BY_ID:
                sel.add(i)
                
        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def get_selected(client_id: str) -> Dict[str, Any]:
        """
            Get classes user has selected to their list.

            Arguments:
                - client_id (str): the users id
        """
        sel = selected_set(client_id)
        return {
            "selected_ids": sorted(sel),
            "items": [DATA_BY_ID[i] for i in sel],
        }
    
    @mcp.tool()
    def remove_from_selected(ids: List[str], client_id: str) -> Dict[str, Any]:
        """
        Remove selected classes from user's list

        ARGUMENTS:
            - ids (List[str]): list of crn codes to remove
            - client_id (str): the users id
        
        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing
        """
        sel = selected_set(client_id)
        for i in ids:
            if i in sel:
                sel.remove(i)
        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def clear_selected(client_id: str) -> Dict[str, Any]:
        """
        Remove all selected classes from user's list

        ARGUMENTS:
            - client_id (str): the users id
        
        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing
        
        """
        sel = selected_set(client_id)
        sel.clear()
        return {"selected_ids": sorted(sel)}
    
    return mcp
