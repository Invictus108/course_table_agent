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

    DATA_BY_ID = {str(item["course_id"]): item for item in data} # id is hash of title

    # Per-client selected list (in-memory, per process)
    SELECTED: Dict[str, set[str]] = {}
    TAKEN: Dict[str, set[str]] = {}

    def selected_set(ctx: Context) -> set[str]:
        key = ctx.client_id or "default"
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
        """

        filters = filters or {}
        out = []

        for item in data:
            ok = True

            # course_code: range [min, max]
            if "course_code" in filters:
                lo, hi = filters["course_code"]
                code = item["listings"][0].get("course_code") if len(item["listings"]) > 0 else ""
                if code != None and len(code.split(" ")) > 1:
                    code = int(code.split(" ")[1])
                else:
                    code = 0
                if code is None or not (lo <= code <= hi):
                    ok = False

            # department: list of strings (ANY match)
            if ok and "department" in filters:
                lis = item.get("listings")
                for l in lis:
                    if l["subject"] in filters["department"]:
                        break
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

            if ok:
                out.append(item)
        
        random.shuffle(out)

        return {"total": len(out), "items": out[:25]}

    @mcp.tool()
    def add_to_selected(ids: List[str], ctx: Context) -> Dict[str, Any]:
        
        """
            Add one or more course IDs to the current user's selected-course list
            (stored in the per-user session context).

            WHEN TO USE:
            - Call this tool when the user explicitly says they want to add/select/save/include
            specific courses in their plan (e.g., “Add CPSC 201 and MATH 222”).
            - Only call after you have concrete course IDs (not just course names).

            ARGUMENTS:
            - ids (List[str]): Course IDs exactly as returned by the course table or search tools, as strings

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
        
        sel = selected_set(ctx)
        for i in ids:
            if i in DATA_BY_ID:
                sel.add(i)
        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def get_selected(ctx: Context) -> Dict[str, Any]:
        """
            Get classes user has selected to their list.

            ARGUMENTS:
        """
        sel = selected_set(ctx)
        return {
            "selected_ids": sorted(sel),
            "items": [DATA_BY_ID[i] for i in sel],
        }
    
    @mcp.tool()
    def remove_from_selected(ids: List[str], ctx: Context) -> Dict[str, Any]:
        """
        Remove selected classes from user's list

        ARGUMENTS:
        
        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing
        """
        sel = selected_set(ctx)
        for i in ids:
            if i in sel:
                sel.remove(i)
        return {"selected_ids": sorted(sel)}

    @mcp.tool()
    def clear_selected(ctx: Context) -> Dict[str, Any]:
        """
        Remove all selected classes from user's list

        ARGUMENTS:
        
        DOES NOT USE:
            - If the user is only browsing or asking for recommendations without choosing
        
        """
        sel = selected_set(ctx)
        sel.clear()
        return {"selected_ids": sorted(sel)}
    
    @mcp.tool()
    def export_to_coursetable(ctx: Context) -> Dict[str, Any]:
        sel = selected_set(ctx)
        return {"selected_ids": sorted(sel), "items": [DATA_BY_ID[i] for i in sel]}

    return mcp
