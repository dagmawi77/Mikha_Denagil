-- Create member accounts for mobile app login
-- Password for all accounts: 12345678
-- Password hash (SHA256): ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f

-- Create account for first member (dagmawi)
INSERT INTO member_accounts (member_id, username, password_hash, account_status)
SELECT 
    id,
    'dagmawi' as username,
    'ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f' as password_hash,
    'Active' as account_status
FROM member_registration 
WHERE id = 1
ON DUPLICATE KEY UPDATE password_hash = 'ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f';

-- Create accounts for other members (username = first name from full_name)
INSERT INTO member_accounts (member_id, username, password_hash, account_status)
SELECT 
    m.id,
    CONCAT('member', m.id) as username,
    'ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f' as password_hash,
    'Active' as account_status
FROM member_registration m
WHERE m.id > 1
AND NOT EXISTS (SELECT 1 FROM member_accounts WHERE member_id = m.id)
LIMIT 10;

-- Show created accounts
SELECT 
    ma.username,
    m.full_name,
    m.section_name,
    ma.account_status
FROM member_accounts ma
JOIN member_registration m ON ma.member_id = m.id;

