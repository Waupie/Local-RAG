# Chat Logger

Simply do this:

docker exec local-rag-timescaledb-1 \
    psql -U postgres -c "SELECT * FROM chat_messages;"


This folder contains the private chat logging functionality for the Local RAG project.

> **Note:** This folder is intended for local/private use and should **not** be committed to GitHub if it contains custom logging logic.

---

## What is stored?

Each user message is saved to the database with:

* Message
* Timestamp

No user identifiers, IP addresses, or AI responses are stored.

---

## Database

The application uses the existing TimescaleDB/PostgreSQL container defined in `docker-compose.yml`.

Connection string:

```text
postgresql://postgres:password@timescaledb:5432/postgres
```

---

## Enter the database

From the project root:

```bash
docker exec -it local-rag-timescaledb-1 psql -U postgres
```

---

## List tables

Inside PostgreSQL:

```sql
\dt
```

Expected output:

```text
documents
chat_messages
```

---

## View stored messages

```sql
SELECT * FROM chat_messages;
```

Newest messages first:

```sql
SELECT *
FROM chat_messages
ORDER BY created_at DESC;
```

---

## Delete all messages

```sql
TRUNCATE TABLE chat_messages;
```

Reset the auto-increment ID as well:

```sql
TRUNCATE TABLE chat_messages RESTART IDENTITY;
```

---

## Count stored messages

```sql
SELECT COUNT(*) FROM chat_messages;
```

---

## Exit PostgreSQL

```sql
\q
```

---

## Docker

View running containers:

```bash
docker ps
```

Restart the application after code changes:

```bash
docker compose up --build
```

Stop everything:

```bash
docker compose down
```

---

## Table schema

```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
