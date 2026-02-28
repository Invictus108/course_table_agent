# filtering can be applied to course code, department, professor rating, difficulty, time (prevent collisions)

# mcp_logic.py
from typing import Any, Dict, List
from mcp.server.fastmcp import Context, FastMCP
import random
import sys

# add rag path
from rag import get_top_k


def bitmask_to_days(mask: int) -> str:
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    return "/".join(day for i, day in enumerate(days, 1) if mask >> i & 1)


def days_to_bitmask(days):
    mapping = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }
    return sum(1 << mapping[day] for day in days if day in mapping)


def create_mcp(data: List[Dict[str, Any]], coure_reqs: List[Dict[str, Any]]) -> FastMCP:
    """
    Factory function.
    The caller provides the dataset.
    """
    mcp = FastMCP(name="InMemoryFilterSelect", json_response=True)

    DATA_BY_ID = {}

    for course in data:
        listings = course.get("listings", [])

        if course.get("course_meetings"):
            for m in course.get("course_meetings"):
                m["days_of_week"] = bitmask_to_days(int(m["days_of_week"]))

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
    def get_majors(client_id: str) -> str:
        """
        Returns a list of majors and their mappings

        This takes no arguemnts and returns a string with all the mappings.
        
        """

        res = """
            Aerospace Studies (USAF)
            African American Studies (AFAM)
            African Studies (AFST)
            Akkadian (AKKD)
            American Sign Language (ASL)
            American Studies (AMST)
            Ancient Greek (GREK)
            Anthropology (ANTH)
            Applied Mathematics (AMTH)
            Applied Physics (APHY)
            Arabic (ARBC)
            Archaeological Studies (ARCG)
            Architecture (ARCH)
            Armenian (ARMN)
            Art (ART)
            Astronomy (ASTR)
            Bengali (BNGL)
            Biological & Biomedical Sci (B&BS)
            Biology (BIOL)
            Biomedical Engineering (BENG)
            Biostatistics (BIS)
            British Studies (BRST)
            Burmese (BURM)
            Catalan (CTLN)
            Cell & Molecular Physiology (C&MP)
            Cell Biology (CBIO)
            Chemical Engineering (CENG)
            Chemistry (CHEM)
            Cherokee (CHER)
            Child Study (CHLD)
            Chinese (CHNS)
            Chronic Disease Epidemiology (CDE)
            Classical Civilization (CLCV)
            Classics (CLSS)
            Clinical Clerkships (MEDR)
            Cognitive Science (CGSC)
            Collections: Objects, Research, Society (COSM)
            Comp Biol & Bioinformatics (CB&B)
            Comparative Literature (CPLT)
            Computer Science (CPSC)
            Computer Science and Economics (CSEC)
            Computing and Linguistics (CSLI)
            Computing and the Arts (CPAR)
            Courses in School of Medicine (MEDC)
            Czech (CZEC)
            Directed Studies (DRST)
            Directing (DIR)
            Diss Research – in Residence (DISR)
            Drama (DRAM)
            Drama Summer (DRMA)
            Dutch (DUTC)
            Early Modern Studies (EMST)
            Earth and Planetary Sciences (EPS)
            East Asian Lang and Lit (EALL)
            East Asian Studies (EAST)
            Ecology & Evolutionary Biology (E&EB)
            Ecology & Evolutionary Biology (EEB)
            Economics (ECON)
            Education Studies (EDST)
            Egyptology (EGYP)
            Electrical & Computer Engineering (EECS)
            Electrical Engineering (ECE)
            Energy Studies (ENRG)
            Engineering & Applied Science (ENAS)
            English (ENGL)
            English Language Program (ELP)
            Environment (ENV)
            Environmental Engineering (ENVE)
            Environmental Health Sciences (EHS)
            Environmental Studies (EVST)
            Epidemiology & Public Health (EPH)
            Epidemiology Microbial Disease (EMD)
            Ethics, Politics, & Economics (EP&E)
            Ethnicity, Race, & Migration (ER&M)
            European & Russian Studies (E&RS)
            Exchange Scholar Experience (EXCH)
            Executive MPH (EMPH)
            Experimental Pathology (EXPA)
            Film & Media Studies (FILM)
            Finnish (FNSH)
            FLPN (FLPN)
            Forestry & Environment Studies (F&ES)
            French (FREN)
            Genetics (GENE)
            Geology and Geophysics (G&G)
            German (GMAN)
            Global Affairs (GLBL)
            Health Policy and Management (HPM)
            Health Sciences (HSCI)
            Health Studies (HLTH)
            Hebrew (HEBR)
            HELN (HELN)
            Hindi (HNDI)
            Hist of Science, Hist of Med (HSHM)
            History (HIST)
            History of Art (HSAR)
            Human Rights (HMRT)
            Humanities (HUMS)
            Hungarian (HGRN)
            Immunobiology (IBIO)
            Ind Res in Sciences (IDRS)
            Indonesian (INDN)
            Interdept Neuroscience Program (INP)
            Investigative Medicine (IMED)
            Italian Studies (ITAL)
            Japanese (JAPN)
            Jewish Studies (JDST)
            Khmer (KHMR)
            Kiswahili (SWAH)
            Korean (KREN)
            Latin (LATN)
            Latin American Studies (LAST)
            Law (LAW)
            Linguistics (LING)
            Literature (LITR)
            Management (MGT)
            Management, PhD (MGMT)
            Master's Thesis Research (MRES)
            Material Hist of Human Record (MHHR)
            Mathematics (MATH)
            Mechanical Engineering (MENG)
            Medieval Studies (MDVL)
            Mesopotamia (MESO)
            Microbiology (MBIO)
            Modern Greek (MGRK)
            Modern Middle East Studies (MMES)
            Modern Tibetan (MTBT)
            Molecular Biophysics & Biochem (MB&B)
            Molecular, Cellular & Dev Biology (MCDB)
            Music Department (MUSI)
            Naval Science (NAVY)
            Near Eastern Langs & Civs (NELC)
            Nepali (NPLI)
            Neuroscience (NSCI)
            Nursing (NURS)
            Ottoman (OTTM)
            Persian (PERS)
            Personalized Med & Applied Engr (PMAE)
            Pharmacology (PHAR)
            Philosophy (PHIL)
            Physician Assistant Online Program (OLPA)
            Physician Associate Program (PA)
            Physics (PHYS)
            Polish (PLSH)
            Political Science (PLSC)
            Portuguese (PORT)
            Practicum Analysis (PRAC)
            Prep for Adv to Candidacy (CAND)
            Preparing for Qualifying Exams (QUAL)
            Psychology (PSYC)
            Public Health (PUBH)
            Public Humanities (PHUM)
            Punjabi (PNJB)
            Quantum Materials Sci & Engr (QMSE)
            Religion (REL)
            Religious Studies (RLST)
            Renaissance Studies (RNST)
            Romanian (ROMN)
            Russian (RUSS)
            Russian & East Europe Studies (RSEE)
            Sanskrit (SKRT)
            School of Medicine (MD)
            School of Music (MUS)
            Science (SCIE)
            Semitic (SMTC)
            Serbian & Croatian (SBCR)
            Sinhala (SNHL)
            Slavic (SLAV)
            Social and Behavioral Sciences (SBS)
            Sociology (SOCY)
            South Asian Studies (SAST)
            Spanish (SPAN)
            Special Divisional Major (SPEC)
            Start Program – Medical School (STRT)
            Statistics and Data Sciences (S&DS)
            Studies in the Environment (STEV)
            Study of the City (STCY)
            Summer Term (SUMR)
            Swedish (SWED)
            Tamil (TAML)
            Theater, Dance, & Performance Studies (THST)
            Theater, Dance, & Performance Studies (TDPS)
            Tibetan (TBTN)
            TLGU (TLGU)
            Translational Biomedicine (PTB)
            Turkish (TKSH)
            Twi (TWI)
            Ukrainian (UKRN)
            Urban Studies (URBN)
            Vietnamese (VIET)
            Visiting Assistant in Research (VAIR)
            Wolof (WLOF)
            Women's, Gender & Sexuality Studies (WGSS)
            Yiddish (YDSH)
            Yoruba (YORU)
            Zulu (ZULU)

            Combined majors
            ------------
            MATH+PHYS - Mathematics + Physics
            CPSC+MATH - Computer Science + Mathematics
            CPSC+PSYC - Computer Science + Psychology
            ECON+MATH - Economics + Mathematics
            MATH+PHIL - Mathematics + Philosophy
            MATH+PHYS - Mathematics + Physics
            PHYS+G&G - Physics + Geosciences 
            PHYS+PHIL - Physics + Philosophy
            EECS - Electrical Engineering and Computer Science


            Certificates (Similar to Minors)
            ------------

            CERT-AFST — African Studies
            CERT-NELC — Near Eastern Languages and Civilizations
            CERT-SAST — South Asian Studies
            CERT-SEAS — Southeast Asia Studies
            CERT-EALL — East Asian Languages and Literatures
            CERT-CLSS — Classics
            CERT-CSS — Climate Science and Solutions
            CERT-COSM — Collections: Objects, Research, Society
            CERT-CPSC — Computer Science (Programming)
            CERT-GMST — German Studies
            CERT-EDST — Education Studies
            CERT-ENRG — Energy Studies
            CERT-ETHNO — Ethnography
            CERT-FOOD — Food, Agriculture, and Climate Change
            CERT-FREN — French
            CERT-GHST — Global Health Studies
            CERT-HR — Human Rights Studies
            CERT-ISLM — Islamic Studies
            CERT-ITAL — Italian Studies
            CERT-MDVL — Medieval Studies
            CERT-PERS — Persian and Iranian Studies
            CERT-PORT — Portuguese
            CERT-QSE — Quantum Science and Engineering
            CERT-RUSS — Russian
            CERT-SPAN — Spanish
            CERT-SDS — Statistics and Data Science
            CERT-TRAN — Translation Studies
                                
            """
        
        return res

    @mcp.tool()
    def query_items(filters: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """
        Queries the Yale course catalog for courses matching the given filters.

        Will return a random sample of 25 courses that match the filters.

        Allowed filters (all optional):

        - course_code:
            Range filter on the numeric portion of the course code.
            Example:
                course_code = [1000, 8000]   # matches courses 1000-8000

        - department:
            One or more department codes (strings).
            Matches courses in ANY of the listed departments.
            Example:
                department = ["CPSC", "MATH"]

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
            An array of day names
            Example:
                days_of_week = ["Tuesday", "Thursday"]

            Will match all courses where the meeting days are a subset of the specified days.

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
                    b1 = days_to_bitmask(days.split("/"))
                    b2 = days_to_bitmask(filters["days_of_week"])
                    if (b1 & b2) == b1:
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
        """
        Get major requirements for a given major code.
        Use when the user mentions a major, requirement, or asks whether courses satisfy degree progress.
        Guidance:
            Check requirements before making strong claims about what a student should take.
            Use requirements to identify missing categories, sequencing concerns, and high-value next courses.
            If the student is undecided between majors, compare requirement structures before recommending a path.

        ARGUMENTS:
            - major_code (str): the major code (EX: CPSC, PHYS, ENGL)

        notes: for combined majors (EX: Math + CS) just combine the codes with a + (MATH+CPSC)

        USE:
            - For finding major requirements
        """
        if major_code not in MAJOR_REQS:
            return "Major code not found"
        else:
            return MAJOR_REQS[major_code]

    @mcp.tool()
    def rag_search(query: str) -> list[dict[str, float | str]]:
        """
        Rag search over pages on yale.edu
        Use to retrieve Yale-specific context from yale.edu sources.
        Especially useful for:
            professor or instructor context,
            labs, research groups, and programs
            departmental policies or advising pages
            distributional or program guidance
            Yale College resources, centers, and opportunities
            relevant Yale news or announcements
            background context that improves recommendations beyond catalog data

        Use to try and find contetual information.

        ARGUMENTS:
           - query (str): search query

        USE:
           - For finding contextual information

        DO NOT USE:
           - For finding courses or major requirments. There are other tools for that.
        """
        return get_top_k(query, k=10)

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
