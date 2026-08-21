# fachbereich-chatbot

## Quick Start

- Clone this repo
- Install docker

### Moodle-DL

Moodle Downloader

- Connect to the moodle-dl container do your settings (recomended: Dont do any connections to email telegram etc) fill in your moodle url, your username and password
- When you get asked if you want to do more settings pick yes
  - In the extended settings choose the courses you want to synchronies in the whitelist
  - Question: For which of the following course do you want to change the settings?
    - Answer: None
  - Question: Do you want to download submissions of your assignments?
    - Recommended Answer: No
  - Question: Would you like to download descriptions of the courses you have selected?
    - Recommended Answer: Yes
  - Question: Do you want to download databases of your courses?
    - Recommended Answer: No
  - Question: Do you want to download forums of your courses?
    - Recommended Answer: Yes (We can filter irrelevant ones out later)
  - Question: Do you want to download quizzes of your courses?
    - Recommended Answer: No
  - Question: Do you want to download lessons of your courses?
    - Recommended Answer: No
  - Question: Do you want to download workshops of your courses?
    - Recommended Answer: No
  - Question: Do you want to download books of your courses?
    - Recommended Answer: No
  - Question: Do you want to download calendars of your courses?
    - Recommended Answer: No
  - Question: Would you like to download linked files of the courses you have selected?
    - Recommended Answer: No
  - Question: Would you like to download files for which a cookie is required?
    - Recommended Answer: No (not sure)

```
docker compose run --rm moodle-dl --init
```

If you didnt did the settings while init or want to change them later you can run the following command to change them after that:

```
docker compose run --rm moodle-dl --config
```

for problems with this container please check: https://github.com/C0D3D3V/Moodle-DL

### Sciebo sync

Optional this syncs a sciebo or nextcloud folder so that the confog csvs can easy be edited by multiple people

in the en file set sciebo url and after the url add `/remote.php/webdav/` for the password create an app password go to sciebo web > settings > security > new app password

### Starting the docker compose

run `docker compose up -d`
