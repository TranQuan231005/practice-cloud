# Serverless Document Vault (AWS SAM & SAM Policy Templates Practice)

Dự án thực hành chuyên sâu về **AWS Serverless Application Model (SAM)**, **AWS Identity & Access Management (IAM)** qua **SAM Policy Templates**, cùng mô hình theo dõi trạng thái (**Observability & State Transitions**).

---

## 1. Kiến trúc & Các thành phần

Hệ thống được thiết kế theo mô hình Serverless hoàn toàn, sử dụng Infrastructure as Code (IaC) thông qua `template.yaml`.

```mermaid
flowchart TD
    Client[HTTP Client / sam local / cURL] -->|HTTP Requests| APIGW[API Gateway - /prod]

    APIGW -->|POST /documents| F1["CreateDocumentFunction<br/>Policy: DynamoDBCrudPolicy"]
    APIGW -->|GET /documents<br/>GET /documents/{id}| F2["GetDocumentFunction<br/>Policy: DynamoDBReadPolicy"]
    APIGW -->|POST /documents/{id}/upload-url| F3["GetUploadUrlFunction<br/>Policy: S3WritePolicy"]
    APIGW -->|PATCH /documents/{id}/status| F4["UpdateDocumentStatusFunction<br/>Policy: DynamoDBCrudPolicy"]

    F1 -->|Write Record| DDB[(DynamoDB: DocumentsTable)]
    F2 -->|Read Record Only| DDB
    F3 -->|Sign Presigned PUT URL| S3[(S3: DocumentsBucket)]
    F4 -->|Update Status & History| DDB
```

---

## 2. Tìm hiểu sâu về SAM Policy Templates

Trong AWS CloudFormation thuần túy, để cấp quyền cho 1 Lambda function, bạn phải viết hàng chục dòng YAML định nghĩa `AWS::IAM::Role` với `AssumeRolePolicyDocument` và `Policies`.

Với AWS SAM, bạn chỉ cần sử dụng thuộc tính `Policies:` ngay trong `AWS::Serverless::Function`:

### 2.1 Các Policy Template được áp dụng trong dự án

| Lambda Function | SAM Policy Template | Quyền hạn cấp dưới nền tảng (CloudFormation IAM Role) | Ranh giới bảo vệ (Least Privilege) |
| :--- | :--- | :--- | :--- |
| **`CreateDocumentFunction`** | `DynamoDBCrudPolicy` | `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Batch*`, `Query`, `Scan` trên bảng `DocumentsTable`. | Không có quyền truy cập S3; không thể xóa/thay đổi cấu trúc bảng. |
| **`GetDocumentFunction`** | `DynamoDBReadPolicy` | `dynamodb:GetItem`, `Scan`, `Query`, `BatchGetItem` trên `DocumentsTable`. | **Chỉ đọc**: Cố gắng ghi (`PutItem`) hay xóa (`DeleteItem`) sẽ bị AWS từ chối ngay lập tức (`AccessDeniedException`). |
| **`GetUploadUrlFunction`** | `S3WritePolicy` | `s3:PutObject`, `s3:PutObjectAcl`, `s3:PutObjectTagging` trên bucket `DocumentsBucket`. | **Chỉ ghi**: Không có quyền đọc file (`GetObject`) hoặc xóa file (`DeleteObject`). |
| **`UpdateDocumentStatusFunction`** | `DynamoDBCrudPolicy` | `dynamodb:UpdateItem`, `GetItem` trên `DocumentsTable`. | Phục vụ cập nhật state transition và ghi nhật ký quan sát (`history`). |

### 2.2 Xem SAM "dịch" Policy Template ra IAM Role như thế nào

Khi bạn chạy lệnh:
```bash
sam build
```
SAM sẽ biên dịch và sinh ra file `.aws-sam/build/template.yaml`. Mở file này ra, bạn sẽ thấy SAM tự động sinh ra một `AWS::IAM::Role` đầy đủ:
```yaml
# Ví dụ IAM Role do SAM sinh tự động cho GetDocumentFunction:
GetDocumentFunctionRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Statement:
        - Action: ['sts:AssumeRole']
          Effect: Allow
          Principal:
            Service: [lambda.amazonaws.com]
    Policies:
      - PolicyName: GetDocumentFunctionRolePolicy0
        PolicyDocument:
          Statement:
            - Action:
                - dynamodb:GetItem
                - dynamodb:BatchGetItem
                - dynamodb:Query
                - dynamodb:Scan
              Effect: Allow
              Resource: !GetAtt DocumentsTable.Arn
```

---

## 3. Quản lý Vòng đời & Quan sát Trạng thái (Observability)

Mỗi document có vòng đời rõ ràng để quan sát luồng xử lý:

```
[PENDING_UPLOAD] ──> [UPLOADED] ──> [PROCESSING] ──> [ACTIVE]
       │                   │              │              │
       └──> [FAILED] <─────┴──────────────┴──────────────┘
              │
              └──> [ARCHIVED]
```

Mỗi lần cập nhật trạng thái qua endpoint `PATCH /documents/{id}/status`, Lambda sẽ:
1. Ghi log có cấu trúc: `[OBSERVABILITY] Document <id> transition: '<from>' -> '<to>'. Reason: <reason>`.
2. Append vào mảng `history` trong DynamoDB gồm: `status`, `previous_status`, `changed_at`, và `reason`.

---

## 4. Hướng dẫn Chạy & Thực hành

### Bước 1: Chạy Unit Tests tự động
Dự án có sẵn bộ unit test độc lập không cần cài đặt cloud:
```bash
python3 -m pytest tests/ -v
```

### Bước 2: Build với AWS SAM CLI
```bash
sam build
```

### Bước 3: Test nhanh từng Lambda bằng mock events (không cần API Gateway)
SAM CLI cho phép giả lập event trực tiếp:
```bash
# Test tạo document
sam local invoke CreateDocumentFunction -e events/create_document_event.json

# Test sinh presigned upload URL
sam local invoke GetUploadUrlFunction -e events/get_upload_url_event.json

# Test cập nhật trạng thái quan sát
sam local invoke UpdateDocumentStatusFunction -e events/update_status_event.json

# Test đọc document
sam local invoke GetDocumentFunction -e events/get_document_event.json
```

### Bước 4: Chạy Local API Server giả lập API Gateway
Nếu máy bạn có Docker đang chạy:
```bash
sam local start-api
```
Sau đó gọi các API qua cURL:
```bash
# 1. Tạo document mới
curl -X POST http://127.0.0.1:3000/documents \
  -H "Content-Type: application/json" \
  -d '{"title": "Báo cáo Thực hành Cloud", "owner": "quan@example.com"}'

# 2. Lấy Presigned URL để upload file lên S3
curl -X POST http://127.0.0.1:3000/documents/<DOCUMENT_ID>/upload-url \
  -H "Content-Type: application/json" \
  -d '{"file_name": "report.pdf", "content_type": "application/pdf"}'

# 3. Chuyển trạng thái sang PROCESSING để quan sát log
curl -X PATCH http://127.0.0.1:3000/documents/<DOCUMENT_ID>/status \
  -H "Content-Type: application/json" \
  -d '{"status": "PROCESSING", "reason": "Hệ thống đang trích xuất dữ liệu"}'

# 4. Xem lại document và lịch sử chuyển trạng thái
curl http://127.0.0.1:3000/documents/<DOCUMENT_ID>
```

### Bước 5: Deploy lên AWS thật (khi sẵn sàng tài khoản AWS)
```bash
sam deploy --guided
```
SAM sẽ hỏi tên stack, region, và tự động tạo toàn bộ S3 Bucket, DynamoDB Table, API Gateway, cùng các IAM execution role có giới hạn quyền chuẩn least-privilege.
