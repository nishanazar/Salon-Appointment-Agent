\# FreshLook Salon — WhatsApp Booking Agent



WhatsApp booking assistant built with OpenClaw, connected to a custom MCP server and Supabase (Postgres) database.



\## Structure

\- database/schema.sql — Postgres schema for Supabase

\- agent/ — MCP server (mcp\_server.py) + Supabase client

\- agent-config/ — Agent personality/behavior rules



\## Setup

1\. Create a Supabase project, run database/schema.sql in SQL Editor

2\. cd agent then pip install -r requirements.txt

3\. Copy .env.example to .env, fill Supabase credentials

4\. Connect via OpenClaw MCP





C:\\Users\\SDC\\salon-project-github>git init

Initialized empty Git repository in C:/Users/SDC/salon-project-github/.git/



C:\\Users\\SDC\\salon-project-github>git add .

warning: in the working copy of 'agent-config/AGENTS.md', LF will be replaced by CRLF the next time Git touches it

warning: in the working copy of 'agent-config/IDENTITY.md', LF will be replaced by CRLF the next time Git touches it

warning: in the working copy of 'agent-config/SOUL.md', LF will be replaced by CRLF the next time Git touches it

warning: in the working copy of 'agent-config/TOOLS.md', LF will be replaced by CRLF the next time Git touches it



C:\\Users\\SDC\\salon-project-github>git status

On branch master



No commits yet



Changes to be committed:

&#x20; (use "git rm --cached <file>..." to unstage)

&#x20;       new file:   .gitignore

&#x20;       new file:   README.md

&#x20;       new file:   agent-config/AGENTS.md

&#x20;       new file:   agent-config/IDENTITY.md

&#x20;       new file:   agent-config/SOUL.md

&#x20;       new file:   agent-config/TOOLS.md

&#x20;       new file:   agent/.env.example

&#x20;       new file:   agent/db\_client.py

&#x20;       new file:   agent/mcp\_server.py

&#x20;       new file:   agent/requirements.txt

&#x20;       new file:   database/schema.sql



