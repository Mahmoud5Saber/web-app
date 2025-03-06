from locust import HttpUser, task, between
import json

class FlaskAppUser(HttpUser):
    wait_time = between(1, 3)  # Wait time between requests

    @task
    def test_home_page(self):
        self.client.get("/")
    
    @task
    def test_app_performance(self):
        self.client.get("/app-performance")
    
    @task
    def test_user_activity(self):
        self.client.get("/user-activity")
    
    @task
    def test_request_analysis(self):
        data = {"request_input": "https://jsonplaceholder.typicode.com/posts/1", "method": "GET"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.client.post("/request-analysis", data=data, headers=headers)

if __name__ == "__main__":
    import os
    os.system("locust -f locust_test.py --headless -u 10 -r 2 --run-time 1m --csv=locust_results")
