// scripts/init-user.js
// Tạo user mẫu cho chức năng đăng nhập
// Sử dụng hash bcrypt đã tạo sẵn cho password 'admin123'
const username = 'admin';
const hashedPassword = '$2b$10$wQwQwQwQwQwQwQwQwQwQwOQwQwQwQwQwQwQwQwQwQwQwQwQwQwQwQw'; // Thay bằng hash thực tế

db = db.getSiblingDB('legal_documents');
db.createCollection('users');
db.users.insertOne({ username: username, password: hashedPassword });
print('User admin created with password admin123');
