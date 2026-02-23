import requests
r = requests.post("https://api.coursetable.com/ferry/v1/graphql", json={"query": """
                                                                        {\n  courses(where: {season_code: {_eq: \"202601\"}}) {\n    title\n    average_workload\n    average_rating\n    description\n    areas\n    course_id\n    course_meetings {\n      days_of_week\n      start_time\n      end_time\n    }\n    listings {\n      crn\n      subject\n    }\n  }\n}
                                                                        """}, headers={"Content-Type":"application/json"})

print(r.status_code, r.text)
