# filtering can be applied to course code, department, professor rating, difficulty, time (prevent collisions)

# mcp_logic.py
from typing import Any, Dict, List
from mcp.server.fastmcp import Context, FastMCP
import random
import sys

# add rag path
sys.path.append("..")
from rag.rag import get_top_k


def create_mcp(data: List[Dict[str, Any]], coure_reqs: List[Dict[str, Any]]) -> FastMCP:
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
                "is_class": not course.get("section").isalpha(),
                "professors": course.get("course_professors"),
                # listing-level fields
                "subject": listing.get("subject"),
                "course_code": listing.get("course_code"),
            }

    MAJOR_REQS = {}
    for course in coure_reqs:
        # check if its a list
        if isinstance(course["subject"], list):
            for s in course["subject"]:
                MAJOR_REQS[s] = course["text"]
        else:
            MAJOR_REQS[course["subject"]] = course["text"]


    # Per-client selected list (in-memory, per process)
    SELECTED: Dict[str, set[str]] = {}

    def selected_set(client_id: str) -> set[str]:
        key = client_id
        if key not in SELECTED:
            SELECTED[key] = set()
        return SELECTED[key]

    # ---- TOOLS ----

    @mcp.tool()
    def query_items(filters: Dict[str, Any], client_id: str) -> Dict[str, Any]:
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

        - average_rating:
            Lower bound (inclusive) on average class rating.
            Example:
                average_rating = 4.2     # rating >= 4.2

        - average_workload:
            Upper bound (inclusive) on course difficulty.
            Example:
                average_workload = 3.5           # difficulty <= 3.5

        - time:
            Range filter on start time (24-hour format).
            Times are integers representing minutes since midnight.
            Example:
                time = [540, 720]           # 9:00–12:00


        - days_of_week:
            An array of bitmask filters on days of the week.
            Example:
                days_of_week = [20]           # Tuesday/Thursday

            Important: Coursetable days_of_week is a bitmask where Monday = 2, Tuesday = 4, Wednesday = 8, Thursday = 16, Friday = 32, Saturday = 64, Sunday = 128.
            A value represents the sum of these (e.g., 20 = 4 + 16 = Tuesday/Thursday).
            Always decode meeting days using this mapping.

        - only_courses:
            A boolean flag to include only actual courses (no sections).
            Example:
                only_courses = True

        - keywords
            List of strings (any match).
            Will match words in course title and description.
            Example:
                keywords = ["machine learning", "artificial intelligence"]
        
        - professors
            List of strings (any match).
            Will match professors.
            Example:
                professors = ["John Doe", "Jane Doe"]
        - make sure to capitalize professor names
        """

        filters = filters or {}
        out = []

        for item in DATA_BY_ID.values():
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
                    pass
                else:
                    ok = False

            # professors: list of strings (ANY match)
            if ok and "professors" in filters:
                profs = item.get("professors")
                if len(profs) == 0:
                    ok = False
                for p in profs:
                    if p["professor"]["name"] in filters["professors"]:
                        break
                else:
                    ok = False
        

            # average_rating: lower bound
            if ok and "average_rating" in filters:
                rating = item.get("average_rating", 0)
                if rating == None:
                    rating = 0
                if rating < filters["average_rating"]:
                    ok = False

            # difficulty: upper bound
            if ok and "average_workload" in filters:
                difficulty = item.get("average_workload", float("inf"))
                if difficulty == None:
                    difficulty = float("inf")
                if difficulty > filters["average_workload"]:
                    ok = False

            if ok and "days_of_week" in filters:
                meetings = item.get("course_meetings")
                found = False
                for m in meetings:
                    days = m["days_of_week"]
                    for d in filters["days_of_week"]:
                        if days == d:
                            found = True
                if not found:
                    ok = False

            # time: range [start, end] (minutes since midnight)
            if ok and "time" in filters:
                meetings = item.get("course_meetings")
                for m in meetings:
                    start_time = m["start_time"]
                    end_time = m["end_time"]
                    if (
                        start_time >= filters["time"][0]
                        and end_time <= filters["time"][1]
                    ):
                        break
                else:
                    ok = False

            if ok and "only_courses" in filters and filters["only_courses"]:
                if not item.get("is_class", True):
                    ok = False

            if ok and "keywords" in filters:
                for k in filters["keywords"]:
                    if (
                        k.lower() in item["title"].lower()
                        or k.lower() in item["description"].lower()
                        or (
                            item.get("course_code")
                            and k.lower() in item["course_code"].lower()
                        )
                    ):
                        break
                else:
                    ok = False

            if ok:
                out.append(item)

        # filter out those with same title
        clean_out = []
        c_titles = set()
        for i in out:
            if i["title"] not in c_titles:
                c_titles.add(i["title"])
                clean_out.append(i)
        out = clean_out

        random.shuffle(out)

        return {"total": len(out), "items": out[:25]}
    
    @mcp.tool()
    def get_major_reqs(major_code: str) -> str:
        '''
        Get major requirements for a given major code.

        ARGUMENTS:
            - major_code (str): the major code (EX: CPSC, PHYS, ENGL)
        
        notes: for combined majors (EX: Math + CS) just combine the codes with a + (MATH+CPSC)

        USE:
            - For finding major requirements
        '''
        if major_code not in MAJOR_REQS:
            return "Major code not found"
        else:
            return MAJOR_REQS[major_code]


    @mcp.tool()
    def rag_search(query: str) -> list[dict[str, float | str]]:
        """
        Rag seatch over pages on Yale.eud

        Use to try and find contetual information.

        ARGUMENTS:
           - query (str): search query

        USE:
           - For finding contextual information

        DO NOT USE:
           - For finding courses or major requirments. There are other tools for that.
        """
        return get_top_k(query)

    @mcp.tool()
    def add_to_selected(ids: List[str], client_id: str) -> Dict[str, Any]:
        """
        Add one or more course IDs to the current user's selected-course list
        (stored in the per-user session context).
        Automatically updates the user's current CourseTable worksheet.

        WHEN TO USE:
        - Call this tool when the user explicitly says they want to add/select/save/include
        specific courses in their plan
        - Only call after you have concrete crns (not just course names).

        ARGUMENTS:
        - ids (List[str]): list of crn codes as strings

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

        Important: Coursetable days_of_week is a bitmask where Monday = 2, Tuesday = 4, Wednesday = 8, Thursday = 16, Friday = 32, Saturday = 64, Sunday = 128.
        A value represents the sum of these (e.g., 20 = 4 + 16 = Tuesday/Thursday).
        Always decode meeting days using this mapping.
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
        Automatically updates the user's current CourseTable worksheet.

        ARGUMENTS:
            - ids (List[str]): list of crn codes to remove

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
        Automatically updates the user's current CourseTable worksheet.

        ARGUMENTS:

        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing

        """
        sel = selected_set(client_id)
        sel.clear()
        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def set_selected(ids: List[str], client_id: str):
        """
        Sets the user's selected courses, based on the provided list of CRNs
        Automatically updates the user's current CourseTable worksheet.

        WHEN TO USE:
        - Call this tool only when you want to set the user's selection to EXACTLY the provided list of courses (replacing any previous selection)
        - Only call after you have concrete crns (not just course names).

        ARGUMENTS:
            - ids (List[str]): list of CRN codes to include in the worksheet

        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing

        """
        sel = selected_set(client_id)
        sel.clear()
        for i in ids:
            if i in DATA_BY_ID:
                sel.add(i)

        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def create_worksheet(name: str, ids: List[str], client_id: str):
        """
        Creates a new CourseTable worksheet, populated with the specified courses.

        WHEN TO USE:
        - Call this tool when the user explicitly says they want to you to create a new worksheet
        - Only call after you have concrete crns (not just course names).

        ARGUMENTS:
            - name (str): the name of the worksheet
            - ids (List[str]): list of crn codes to include in the worksheet

        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing

        """
        sel = selected_set(client_id)
        sel.clear()
        for i in ids:
            if i in DATA_BY_ID:
                sel.add(i)

        return {"selected_ids": sorted(sel)}

    return mcp
