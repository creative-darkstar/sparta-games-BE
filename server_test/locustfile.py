from locust import HttpUser, task, between, TaskSet


class UserBehavior(TaskSet):
    @task
    def get_user_detail(self):
        user_id = 1
        self.client.get(f'users/api/{user_id}')


class LocustUser(HttpUser):
    # host = "http://127.0.0.1:8000/"
    host = "http://host.docker.internal:8000/"
    tasks = [UserBehavior]
    wait_time = between(1, 4)
