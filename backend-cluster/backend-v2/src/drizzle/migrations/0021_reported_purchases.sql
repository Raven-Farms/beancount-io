CREATE TABLE "reported_purchases" (
	"invoice_id" text PRIMARY KEY NOT NULL,
	"reported_at" timestamp DEFAULT now() NOT NULL
);
