CREATE TABLE "sent_billing_emails" (
	"key" text PRIMARY KEY NOT NULL,
	"sent_at" timestamp DEFAULT now() NOT NULL
);
