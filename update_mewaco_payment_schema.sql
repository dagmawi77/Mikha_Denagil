-- Add Chapa payment columns to mewaco_contributions table
ALTER TABLE mewaco_contributions
ADD COLUMN IF NOT EXISTS tx_ref VARCHAR(100) COMMENT 'Chapa transaction reference',
ADD COLUMN IF NOT EXISTS chapa_reference VARCHAR(100) COMMENT 'Chapa payment reference',
ADD COLUMN IF NOT EXISTS chapa_response TEXT COMMENT 'Full Chapa API response JSON',
ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100) COMMENT 'Chapa transaction ID',
ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'Pending' COMMENT 'Payment status: Pending, Completed, Paid, Failed',
ADD COLUMN IF NOT EXISTS paid_at TIMESTAMP NULL COMMENT 'Payment completion timestamp',
ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45) COMMENT 'IP address of payment request',
ADD COLUMN IF NOT EXISTS user_agent TEXT COMMENT 'User agent of payment request';

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_tx_ref ON mewaco_contributions(tx_ref);
CREATE INDEX IF NOT EXISTS idx_payment_status ON mewaco_contributions(payment_status);
CREATE INDEX IF NOT EXISTS idx_chapa_ref ON mewaco_contributions(chapa_reference);

