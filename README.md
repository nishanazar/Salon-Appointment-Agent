# FreshLook Salon — WhatsApp Booking Agent

An AI-powered WhatsApp assistant that handles the full appointment lifecycle for a hair and beauty salon — checking availability, booking, cancelling, rescheduling, and sending reminders — with no human receptionist in the loop for routine requests.

## Problem

Salons rely on manual phone calls to manage bookings. This leads to missed calls, double-bookings, and no after-hours availability. Customers increasingly prefer messaging over calling, but most salons have no automated way to handle that channel.

## Solution

A conversational AI agent, reachable directly on WhatsApp, that understands natural language (including Roman Urdu/English mix), checks real-time availability, and completes bookings — grounded entirely in a live database rather than free-form generation.

## Architecture

```
WhatsApp (customer)
      |
      v
OpenClaw (self-hosted agent gateway)
      |  tool calls (MCP)
      v
Python MCP Server ---- Supabase (Postgres)
      |                     ^
      v                     |
 Cron scheduler ---- proactive reminders
      |
      v
Next.js Dashboard (owner-facing, reads the same database)
```

The WhatsApp agent and the owner dashboard are independent surfaces that share one Supabase database as their single source of truth — either can be extended or replaced without touching the other.

## Key Features

- **Natural-language booking** — services, pricing, and availability answered from live data, never guessed
- **Double-booking prevention** — enforced at the database level with a Postgres exclusion constraint, not just application logic
- **Cancellation & rescheduling** — phone-number-verified, so a customer can only modify their own appointment
- **Proactive reminders** — a cron job checks for upcoming appointments and sends a WhatsApp reminder automatically, with duplicate-send protection
- **Owner dashboard** — live appointment list, service/staff/hours management, and a "Mark Complete" human-in-the-loop step so the AI never unilaterally claims a service was delivered
- **Observability** — every tool call is logged and viewable from an in-dashboard activity feed, filterable by day
- **Automated tests** — pytest suite covering booking, double-booking rejection, cancellation ownership, and reschedule conflicts

## Tech Stack

| Layer | Technology |
|---|---|
| Agent runtime | OpenClaw (self-hosted) |
| Messaging | WhatsApp |
| Tool layer | Model Context Protocol (MCP), Python |
| Database | Supabase (Postgres) |
| Dashboard | Next.js, TypeScript, Tailwind CSS |
| Automation | OpenClaw cron scheduler |
| Testing | pytest |

## Repository Structure

```
database/
  schema.sql          Postgres schema - tables, constraints, seed data
agent/
  mcp_server.py         MCP tool definitions exposed to OpenClaw
  db_client.py          Supabase data access layer
  tests/                pytest suite
  requirements.txt
agent-config/
  SOUL.md               Agent personality and behavioral rules
  AGENTS.md             Operating rules and boundaries
  TOOLS.md              Environment-specific tool notes
  IDENTITY.md           Agent identity
dashboard/
  app/                  Next.js pages (appointments, services, staff, hours, activity)
  lib/                  Supabase client
```

## Setup

**1. Database**
Create a Supabase project and run `database/schema.sql` in the SQL Editor.

**2. Agent**
```bash
cd agent
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase credentials
```
Register the MCP server with OpenClaw:
```bash
openclaw mcp add salon-booking --command python --arg mcp_server.py --cwd <path-to-agent>
```

**3. Dashboard**
```bash
cd dashboard
npm install
cp .env.local.example .env.local   # fill in Supabase credentials
npm run dev
```

**4. Tests**
```bash
cd agent
pytest tests/ -v
```

## Disclosure

This project uses OpenClaw (an open-source, self-hosted agent framework) as the messaging/agent gateway, and Supabase for managed Postgres hosting. The database schema, MCP tool integration, cancellation/reschedule safety logic, reminder scheduling, dashboard, and test suite were designed and implemented by our team.

## Status

Core booking flow, cancellation, rescheduling, and reminders are implemented and tested. Production deployment to a persistent server (rather than local execution) is a documented next step.