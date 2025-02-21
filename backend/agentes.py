from fake_useragent import UserAgent

ua = UserAgent()
random_user_agent = ua.random
print(random_user_agent)