USE flytau;

-- ==========================================================
-- Clean up existing data (Reset tables)
-- This ensures we don't get duplicate errors when re-running the script
-- ==========================================================
SET FOREIGN_KEY_CHECKS = 0; -- Temporarily disable FK checks to allow truncate
TRUNCATE TABLE Employees;
TRUNCATE TABLE Aircraft;
TRUNCATE TABLE Roles;
SET FOREIGN_KEY_CHECKS = 1; -- Re-enable FK checks

-- ==========================================================
-- 1. Insert Roles
-- Define the 3 main roles for the system
-- ==========================================================
INSERT INTO Roles (Role_ID, Role_Name) VALUES
(1, 'Admin'),
(2, 'Pilot'),
(3, 'Flight Attendant');

-- ==========================================================
-- 2. Insert Aircraft
-- Adding 6 aircrafts of different manufacturers (Boeing, Airbus, Embraer)
-- ==========================================================
INSERT INTO Aircraft (Manufacturer, Size, Purchase_Date) VALUES
('Boeing', 189, '2019-05-15'),  -- 737-800
('Boeing', 290, '2020-11-20'),  -- 787 Dreamliner
('Airbus', 150, '2021-01-10'),  -- A320
('Airbus', 350, '2018-06-30'),  -- A350
('Boeing', 416, '2017-03-22'),  -- 747-8
('Embraer', 110, '2022-08-12'); -- E195

-- ==========================================================
-- 3. Insert Employees
-- Role IDs: 1=Admin, 2=Pilot, 3=Attendant
-- ==========================================================

-- >> Insert 2 Admins
INSERT INTO Employees (ID_Number, First_name, Last_name, Phone_Number, City, Street, House_No, Employment_Start_Date, Role_id, Login_Password) VALUES
(1001, 'Sela', 'Boss', '050-1000001', 'Tel Aviv', 'Rothschild', '10', '2020-01-01', 1, 'admin123'),
(1002, 'Dana', 'Manager', '050-1000002', 'Haifa', 'Herzl', '5', '2021-02-01', 1, 'admin123');

-- >> Insert 10 Pilots (Role ID: 2)
-- Note: Some are certified for Long Haul flights (1) and some are not (0)
INSERT INTO Employees (ID_Number, First_name, Last_name, Phone_Number, City, Street, House_No, Employment_Start_Date, Role_id, Long_Haul_Certified, Login_Password) VALUES
(2001, 'Avi', 'Cohen', '052-2000001', 'Raunana', 'Ahuza', '1', '2015-05-10', 2, 1, 'pilot123'),
(2002, 'Yael', 'Levi', '052-2000002', 'Tel Aviv', 'Dizengoff', '2', '2016-06-11', 2, 1, 'pilot123'),
(2003, 'Ronen', 'Bar', '052-2000003', 'Givatayim', 'Katznelson', '3', '2017-07-12', 2, 0, 'pilot123'),
(2004, 'Noa', 'Shahar', '052-2000004', 'Holon', 'Sokolov', '4', '2018-08-13', 2, 1, 'pilot123'),
(2005, 'Dan', 'Peled', '052-2000005', 'Bat Yam', 'HaAtzmaut', '5', '2019-09-14', 2, 0, 'pilot123'),
(2006, 'Shira', 'Gol', '052-2000006', 'Rishon', 'Jabotinsky', '6', '2020-10-15', 2, 1, 'pilot123'),
(2007, 'Omer', 'Tal', '052-2000007', 'Herzliya', 'Hanassi', '7', '2021-11-16', 2, 0, 'pilot123'),
(2008, 'Michal', 'Shir', '052-2000008', 'Netanya', 'Herzl', '8', '2022-12-17', 2, 1, 'pilot123'),
(2009, 'Tom', 'Oz', '052-2000009', 'Kfar Saba', 'Weizman', '9', '2023-01-18', 2, 0, 'pilot123'),
(2010, 'Gal', 'Raz', '052-2000010', 'Petah Tikva', 'Baron', '10', '2014-02-19', 2, 1, 'pilot123');

-- >> Insert 20 Flight Attendants (Role ID: 3)
INSERT INTO Employees (ID_Number, First_name, Last_name, Phone_Number, City, Street, House_No, Employment_Start_Date, Role_id, Login_Password) VALUES
(3001, 'Dail', 'One', '054-3000001', 'Eilat', 'Tmarim', '1', '2023-01-01', 3, 'crew123'),
(3002, 'Dail', 'Two', '054-3000002', 'Dimona', 'Ben Gurion', '2', '2023-01-02', 3, 'crew123'),
(3003, 'Dail', 'Three', '054-3000003', 'Beer Sheva', 'Rager', '3', '2023-01-03', 3, 'crew123'),
(3004, 'Dail', 'Four', '054-3000004', 'Ashdod', 'Herzl', '4', '2023-01-04', 3, 'crew123'),
(3005, 'Dail', 'Five', '054-3000005', 'Ashkelon', 'Eli Cohen', '5', '2023-01-05', 3, 'crew123'),
(3006, 'Dail', 'Six', '054-3000006', 'Rehovot', 'Herzl', '6', '2023-01-06', 3, 'crew123'),
(3007, 'Dail', 'Seven', '054-3000007', 'Ramla', 'Herzl', '7', '2023-01-07', 3, 'crew123'),
(3008, 'Dail', 'Eight', '054-3000008', 'Lod', 'Herzl', '8', '2023-01-08', 3, 'crew123'),
(3009, 'Dail', 'Nine', '054-3000009', 'Yavne', 'Herzl', '9', '2023-01-09', 3, 'crew123'),
(3010, 'Dail', 'Ten', '054-3000010', 'Hadera', 'Herzl', '10', '2023-01-10', 3, 'crew123'),
(3011, 'Dail', 'Eleven', '054-3000011', 'Afula', 'Herzl', '11', '2023-01-11', 3, 'crew123'),
(3012, 'Dail', 'Twelve', '054-3000012', 'Tiberias', 'Herzl', '12', '2023-01-12', 3, 'crew123'),
(3013, 'Dail', 'Thirteen', '054-3000013', 'Safed', 'Herzl', '13', '2023-01-13', 3, 'crew123'),
(3014, 'Dail', 'Fourteen', '054-3000014', 'Kiryat Shmona', 'Herzl', '14', '2023-01-14', 3, 'crew123'),
(3015, 'Dail', 'Fifteen', '054-3000015', 'Karmiel', 'Herzl', '15', '2023-01-15', 3, 'crew123'),
(3016, 'Dail', 'Sixteen', '054-3000016', 'Nahariya', 'Herzl', '16', '2023-01-16', 3, 'crew123'),
(3017, 'Dail', 'Seventeen', '054-3000017', 'Akko', 'Herzl', '17', '2023-01-17', 3, 'crew123'),
(3018, 'Dail', 'Eighteen', '054-3000018', 'Kiryat Gat', 'Herzl', '18', '2023-01-18', 3, 'crew123'),
(3019, 'Dail', 'Nineteen', '054-3000019', 'Kiryat Malakhi', 'Herzl', '19', '2023-01-19', 3, 'crew123'),
(3020, 'Dail', 'Twenty', '054-3000020', 'Sderot', 'Herzl', '20', '2023-01-20', 3, 'crew123');