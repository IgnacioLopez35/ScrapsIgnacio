def scrape_profile(self, username):
        """
        Extrae posts del perfil de Instagram especificado.
        """
        self.driver.get(f"https://www.instagram.com/{username}/")
        self._human_delay(3, 5)

        all_posts = []
        last_date = datetime.now()

        while last_date.year >= YEAR_FILTER:
            self._scroll_human()
            new_posts = self._extract_posts()
            if not new_posts:
                break

            for post in new_posts:
                post_date = datetime.strptime(post['date'], "%Y-%m-%dT%H:%M:%S")
                if post_date.year < YEAR_FILTER:
                    return all_posts
                all_posts.append(post)

            last_date = datetime.strptime(new_posts[-1]['date'], "%Y-%m-%dT%H:%M:%S")

        return all_posts
    

    def _extract_posts(self):
        """
        Extrae los datos de los posts visibles.
        """
        posts_data = []
        articles = self.driver.find_elements(By.TAG_NAME, "article")
        if not articles:
            return posts_data

        for article in articles[-6:]:
            try:
                time_element = article.find_element(By.TAG_NAME, "time")
                date_str = time_element.get_attribute("datetime")
                link_elem = article.find_element(By.TAG_NAME, "a")
                post_url = link_elem.get_attribute("href")

                posts_data.append({
                    "date": date_str,
                    "url": post_url
                })
            except Exception as e:
                print("[ERROR] extrayendo post:", e)
                continue

        return posts_data

    def save_to_csv(self, data, filename):
        """
        Guarda los datos extraídos en un archivo CSV.
        """
        if not data:
            print("No hay datos para guardar en CSV.")
            return
        keys = data[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        print(f"[INFO] Se guardaron {len(data)} filas en {filename}.")


