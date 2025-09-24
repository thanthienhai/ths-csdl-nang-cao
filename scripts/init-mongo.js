// MongoDB initialization script
db = db.getSiblingDB('legal_documents');

// Create collections
db.createCollection('documents');

// Create indexes for better performance
db.documents.createIndex({ "title": "text", "content": "text", "summary": "text" });
db.documents.createIndex({ "category": 1 });
db.documents.createIndex({ "date_created": -1 });
db.documents.createIndex({ "tags": 1 });

// Insert sample documents
db.documents.insertMany([
  {
    title: "Bộ luật Lao động 2019 - Quy định về hợp đồng lao động",
    content: "Hợp đồng lao động là thỏa thuận giữa người lao động và người sử dụng lao động về việc làm, tiền lương và điều kiện làm việc. Hợp đồng lao động được ký kết bằng văn bản trong các trường hợp sau đây: a) Hợp đồng lao động có thời hạn từ đủ 01 tháng trở lên; b) Hợp đồng lao động theo mùa vụ hoặc theo một công việc nhất định có thời hạn dưới 01 tháng nhưng người sử dụng lao động hoặc người lao động yêu cầu ký kết bằng văn bản.",
    summary: "Quy định về hợp đồng lao động, điều kiện ký kết và hình thức hợp đồng",
    category: "Luật Lao động",
    tags: ["hợp đồng lao động", "người lao động", "người sử dụng lao động"],
    date_created: new Date(),
    metadata: { source: "Bộ luật Lao động 2019", article: "Điều 15" }
  },
  {
    title: "Bộ luật Dân sự 2015 - Thời hiệu khởi kiện",
    content: "Thời hiệu khởi kiện là thời hạn mà trong đó đương sự có quyền yêu cầu Tòa án giải quyết vụ việc dân sự để bảo vệ quyền, lợi ích hợp pháp của mình. Thời hiệu khởi kiện chung là 03 năm, kể từ ngày quyền, lợi ích hợp pháp bị xâm phạm. Thời hiệu khởi kiện đối với một số vụ việc cụ thể: a) 01 năm đối với vụ việc về bồi thường thiệt hại ngoài hợp đồng; b) 02 năm đối với vụ việc về bồi thường thiệt hại do vi phạm hợp đồng; c) 05 năm đối với vụ việc về quyền sở hữu bất động sản.",
    summary: "Quy định về thời hiệu khởi kiện trong các vụ việc dân sự",
    category: "Luật Dân sự", 
    tags: ["thời hiệu", "khởi kiện", "tòa án", "bồi thường"],
    date_created: new Date(),
    metadata: { source: "Bộ luật Dân sự 2015", article: "Điều 147" }
  }
]);

print('Database initialized successfully!');