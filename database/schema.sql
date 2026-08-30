-- Enable btree_gist extension for exclusion constraint
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- Drop existing tables (in correct FK order) so we start fresh
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS working_hours CASCADE;
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Staff table
CREATE TABLE staff (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Services table
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Working hours table
CREATE TABLE working_hours (
    id SERIAL PRIMARY KEY,
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    UNIQUE(day_of_week)
);

-- Appointments table with exclusion constraint to prevent double-booking
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    staff_id INTEGER REFERENCES staff(id),
    service_id INTEGER REFERENCES services(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmed' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed')),
    created_at TIMESTAMP DEFAULT NOW(),
    EXCLUDE USING gist (
        staff_id WITH =,
        tsrange(start_time, end_time) WITH &&
    ) WHERE (status = 'confirmed')
);

-- Insert sample services
INSERT INTO services (name, duration_minutes, price, description, active) VALUES
('Haircut', 30, 500.00, 'Basic haircut with styling', TRUE),
('Hair Color', 90, 1500.00, 'Full hair coloring service', TRUE),
('Beard Trim', 20, 300.00, 'Beard shaping and trimming', TRUE),
('Facial', 60, 800.00, 'Deep cleansing facial treatment', TRUE);

-- Insert sample staff
INSERT INTO staff (name, phone, active) VALUES
('Rahul Kumar', '9876543210', TRUE),
('Amit Singh', '9876543211', TRUE);

-- Insert working hours (0=Sunday, 6=Saturday)
-- Weekdays: 11:00 - 20:00
INSERT INTO working_hours (day_of_week, start_time, end_time) VALUES
(0, '11:00', '20:00'),
(1, '11:00', '20:00'),
(2, '11:00', '20:00'),
(3, '11:00', '20:00'),
(4, '11:00', '20:00'),
(5, '11:00', '22:00'),
(6, '11:00', '22:00')
ON CONFLICT (day_of_week) DO UPDATE SET start_time = EXCLUDED.start_time, end_time = EXCLUDED.end_time;

-- Verify tables created
DO $$
BEGIN
    RAISE NOTICE 'Tables created successfully!';
    RAISE NOTICE 'Services: %', (SELECT COUNT(*) FROM services);
    RAISE NOTICE 'Staff: %', (SELECT COUNT(*) FROM staff);
    RAISE NOTICE 'Working Hours: %', (SELECT COUNT(*) FROM working_hours);
END $$;
