CREATE TABLE "auth_mail" (
	"id" text PRIMARY KEY NOT NULL,
	"kind" text NOT NULL,
	"payload" text NOT NULL,
	"attempts" integer DEFAULT 0 NOT NULL,
	"available_at" timestamp with time zone DEFAULT now() NOT NULL,
	"expires_at" timestamp with time zone NOT NULL,
	"lease_token" text,
	"lease_until" timestamp with time zone,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "auth_mail_available_idx" ON "auth_mail" USING btree ("available_at");--> statement-breakpoint
CREATE INDEX "auth_mail_expiry_idx" ON "auth_mail" USING btree ("expires_at");