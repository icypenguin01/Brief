# Brief – Sharpen your pentest methodology.

**By capturing, analyzing, and learning from every command you execute.**

**`Brief is a command-line tool` that records your terminal activity during CTF challenges or lab exercises and leverages AI to
produce a structured, in-depth report.**

*It uses a free `Hugging Face account` and the free model `openai/gpt-oss-120b:novita`.*

*Instead of focusing solely on solving the challenge or Box,* **it evaluates your workflow, decision-making process, and technical approach providing actionable feedback to help you refine and improve your performance over time.**

## Easy to use

`just clone the repo` → `export HUGGING FACE TOKEN` → `brief --start` → solve the box → `brief --stop` *(from any terminal or tab)* → `brief -i <file_name>`

---

> Brief is not a vulnerability scanner.

**It is:**
* A methodology auditor
* A command-level performance reviewer
* A workflow stabilizer
* A discipline enforcer

**It analyzes how you operate under pressure and corrects it.**
‎‎
___

### If `walkthroughs` *show you how others solved a box*, `Brief` shows you how you approached it and how to approach it better next time.‎‎
___

##  What It Does
* Most security tools help you find vulnerabilities. **`Brief` helps you fix your methodology.**

**It does not:**
 *Solve the box for you OR Generate exploits automatically OR Replace your thinking OR  Create a Documentation*

* Instead, **it analyzes your behavior** 
**every command,every repetition,every shortcut**  and evaluates how disciplined, efficient, and reproducible your workflow is.

## After Each Session

**Brief** acts like a strict but helpful mentor by:

1. Pointing out every mistake you made
2. Explaining why it was wrong and showing you a better approach
3. Demonstrating the correct methodology and where you went wrong
4. Identifying inefficient commands you used

It then generates a detailed report in both `.md` and `.html` formats. 

[View a sample report →](https://icypenguin01.github.io/Brief/sample-report.html)
___
   
*In CTFs and pentest labs, most learners focus on one thing:*

> “Did I get the flag?”

But exams and *real-world engagements don’t reward luck or chaotic trial-and-error*.

They reward:
* Structured enumeration
* Hypothesis-driven testing
* Clean output management
* Safe validation steps
* Repeatable workflows

Without structured feedback, bad habits compound:

* Re-running scans without saving output
* Blind payload guessing
* Skipping validation steps
* Executing scripts without reviewing them
* Brute-forcing before enumerating

`Brief` **surfaces these habits immediately before they become permanent.**

##  Who Benefits Most
**You’ll get the highest value from `Brief` if:**

* You’re preparing for `OSCP / CPTS-style` exams
* You want to eliminate chaotic trial-and-error habits
* You want structured improvement without enrolling in a course
* You want measurable refinement of your workflow

> If your goal is to become more methodical not just faster this tool is built for you.

## How AI is used

`Brief` uses an open-source large language model served through the `Hugging Face API` ( `openai/gpt-oss-120b:groq`).

When you run `--ingest or --latest`, your recorded terminal session is sent to this model for analysis. 

**The model does not attempt to solve the challenge. Instead, it evaluates**:

* Command selection
* Flag usage
* Output management
* Workflow structure
* Redundant or inefficient behavior
* Risky execution patterns

And It generates a detailed report in `.md (Markdown)` and `.html` formats.

## Quick Start

### 1. Install

```bash
git clone https://github.com/icypenguin01/Brief.git
```
```bash
cd Brief
```
```bash
chmod +x requirements.sh
```
```bash
 ./requirements.sh
```

### If `requirements.sh` doesn't work:

```bash
python3 -m venv ~/.brief/venv
```
```bash
~/.brief/venv/bin/python -m pip install --upgrade pip
```
```bash
~/.brief/venv/bin/python -m pip install openai
```
now rerun `./requirements.sh`

### 2. Get a Hugging Face API Token

1. Visit: https://huggingface.co/settings/tokens
2. Click "New token"
3. Select "Read" permissions
4. Click "Create Token"
5. Copy the token (starts with `hf_`)

### 3. Set Your Token

```bash
export HF_TOKEN= Your Hugging Face Token
```

##  Basic Commands

### Start a new session

```bash
brief --start
```


### Stop a session

```bash
brief --stop
```

### List your most recent session

```bash
brief --list
```

Outputs the full path of the latest session file.

### if you want to use existing session to save new history then use

```bash
brief --use <session name>
```

### Analyze a session (ingesting) [this will give you detailed report in html and .md]

```bash
brief --ingest ~/.brief/sessions/htb-example-box.md
```

It then generates a detailed report in both `.md` and `.html` formats. 

[View a sample report →](https://icypenguin01.github.io/Brief/sample-report.html)

### ingest the most recent session:

```bash
brief --latest
```

### View help

```bash
brief --help
```
##  Workflow Example

### 1. Start your challenge

```bash
brief --start
# Enter name: htb-mysql-injection
# New shell opens, recording begins
```

### 2. Do your work (open a new tab or terminal it can save all history until you type `brief --stop`)
### for example From here you started sloving a box⬇️⬇️
```bash
# Recon
nmap -sS -sV -p- 10.10.10.20

# Enumeration
curl http://10.10.10.20
gobuster dir -u http://10.10.10.20 -w /usr/share/wordlists/dirb/common.txt

# Exploitation
curl http://10.10.10.20/?page=../../../../etc/passwd

# Reverse shell
nc -lvnp 4444
curl http://10.10.10.20/?cmd=bash+-i+...

# Post-exploitation
linpeas.sh
sudo -l
cat /root/root.txt
```
### and here you get root and you want to stop saving history ⬆️⬆️

# Then just Type when done
```bash
brief --stop
```

### 3. Get analysis

```bash
brief --latest
```
### OR 

```bash
brief -i <~/.brief/sessions/htb-mysql-injection.md> (When you end a session, it shows the location of the stored session file.use that session file,)
```
The tool:
- Queries the AI model (takes ~10-20 seconds)
- It Generates `htb-mysql-injection.analysis.md` (Markdown) (you can open in any text editor)
- It Generates `htb-mysql-injection.analysis.html` (styled HTML) (you can open this using firefox or chrome)

### 4. Read the report

[View a sample report →](https://icypenguin01.github.io/Brief/sample-report.html)

```bash
# Plain text
cat ~/.brief/outputs/htb-mysql-injection.analysis.md

# Or open in browser
firefox ~/.brief/outputs/htb-mysql-injection.analysis.html
```

##  Privacy & Security

- **Local storage**: All session files are stored on your machine in `~/.brief/`
- **Selective transmission**: Data is sent to Hugging Face *only* when you run `--ingest` or `--latest` to create report on your history.  
- **API token**: Used only to authenticate with Hugging Face;
---

## screenshots
<img width="1849" height="1011" alt="1" src="https://github.com/user-attachments/assets/51caaabf-4f79-4cc8-b8e8-187c83caa171" />
<img width="1744" height="942" alt="2" src="https://github.com/user-attachments/assets/66e7c1c8-4b03-44c2-87b4-6337c3aa70fe" />
<img width="1919" height="1028" alt="3" src="https://github.com/user-attachments/assets/8eac4c60-c03f-44b4-a2cc-6c0246fae42b" />
<img width="1918" height="934" alt="4" src="https://github.com/user-attachments/assets/d7d27bc1-44c0-41ab-b383-1dfad0e2daa9" />

## 🛠 Troubleshooting
## hugging face api token not found
<img width="1120" height="845" alt="5" src="https://github.com/user-attachments/assets/99376df2-e129-42c2-ab4b-f8cf7ca755ef" />

### Commands not recording?

1. Make sure you started with `brief --start` (not `--use`)
2. Verify you're in the shell that was opened by Brief

### Commands are recording but analysis is empty or slow?

1. Ensure you have internet access
2. Check that `HF_TOKEN` is set: `echo $HF_TOKEN`
3. Verify the token is valid (visit https://huggingface.co/settings/tokens)
4. If the session is very large (1000+ commands), it may take longer

### "No sessions found"

- Run `brief --start` to create a new session first
- Check that `~/.brief/sessions/` directory exists and contains `.md` files

### API token errors?

1. Double-check the token format: `hf_xxxxxxxxxxxxxxxx...`
2. Regenerate a new token if needed
3. Make sure it's set before running `brief --latest`: `echo $HF_TOKEN | head -c 10`

## See the Demo of 'Brief'

<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
  <iframe 
    src="https://www.youtube.com/embed/IDue3Il553E"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
    frameborder="0"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
    allowfullscreen>
  </iframe>
</div>
