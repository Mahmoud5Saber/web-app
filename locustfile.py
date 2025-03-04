from locust import HttpUser, task, between

class FlaskAppUser(HttpUser):
    wait_time = between(1, 3)  

    @task
    def test_homepage(self):
        self.client.get("/")  

    @task
    def test_performance_data(self):
        self.client.get("/performance-data")  

    @task
    def test_api_post(self):
        headers = {"Content-Type": "application/json"}
        payload = {"input": "test_data"}
        self.client.post("/api", json=payload, headers=headers)  

    @task
    def test_health_check(self):
        self.client.get("/health")  
