INSERT INTO sources (name, url, source_type) VALUES
('MIT Technology Review', 'https://www.technologyreview.com/feed/', 'rss'),
('IEEE Spectrum', 'https://spectrum.ieee.org/rss', 'rss'),
('Hackaday', 'https://hackaday.com/feed/', 'rss'),
('Ars Technica', 'https://arstechnica.com/feed/', 'rss'),
('TechCrunch', 'https://techcrunch.com/feed/', 'rss'),
('SpaceX', 'https://www.spacex.com/updates/rss', 'rss'),
('3D Printing Industry', 'https://3dprintingindustry.com/feed/', 'rss'),
('The Drive - War Zone', 'https://www.thedrive.com/the-war-zone/rss', 'rss');

-- Tier 1 X users (new tweets only, max 5 per user)
INSERT INTO x_users (username, tier) VALUES
('PalmerLuckey', 1),
('isaiah_p_taylor', 1),
('Dkirtley', 1),
('billythalheimer', 1),
('ThomasHealyCEO', 1);
