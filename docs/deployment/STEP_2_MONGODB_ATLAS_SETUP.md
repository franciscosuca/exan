# Step 2: MongoDB Atlas Setup

Step-by-step guide to provisioning a MongoDB Atlas database cluster and saving the connection URI in Secret Manager.

Back to: [docs/deployment/DEPLOYMENT_OPTIONS.md](docs/deployment/DEPLOYMENT_OPTIONS.md#rollout-checklist)

---

## 1. Create MongoDB Atlas Project & Free Cluster

1. Sign in to [MongoDB Atlas Console](https://cloud.mongodb.com/).
2. Create a new organization/project named `Exan`.
3. Click **Create Cluster** and choose **M0 (Shared/Free)**.
4. Select Cloud Provider **Google Cloud (GCP)** and region matching Cloud Run (e.g., `us-central1` / `iowa`).
5. Set Cluster Name to `exan-cluster-beta` and click **Create Cluster**.

---

## 2. Create Database User

1. Navigate to **Security** → **Database Access**.
2. Click **Add New Database User**:
   - **Authentication Method**: Password.
   - **Username**: `exan_app`.
   - **Password**: Generate a secure password (record this value).
   - **Database User Privileges**: `readWrite` on the `exan` database (or `Built-in: Read and write to any database`).
3. Click **Add User**.

---

## 3. Configure Network Access

1. Navigate to **Security** → **Network Access**.
2. Click **Add IP Address**.
3. Select **Allow Access from Anywhere** (`0.0.0.0/0`) with description `Cloud Run dynamic egress`.
4. Click **Confirm**.

*(Note: Atlas user authentication and TLS encryption secure the connection. For strict IP restriction, set up GCP Serverless VPC Access with Cloud NAT static IPs in future iterations.)*

---

## 4. Retrieve Connection String

1. Navigate to **Database** → **Clusters**.
2. Click **Connect** on `exan-cluster-beta`.
3. Choose **Drivers** (Node.js / Python).
4. Copy the connection string in the format:
   ```text
   mongodb+srv://exan_app:<PASSWORD>@exan-cluster-beta.xxxx.mongodb.net/exan?retryWrites=true&w=majority&appName=exan-cluster-beta
   ```
5. Replace `<PASSWORD>` with the actual database user password.

---

## 5. Store Connection URI in GCP Secret Manager

```bash
# Create the MONGO_URI secret
gcloud secrets create MONGO_URI \
  --replication-policy="automatic"

# Add the secret payload version
echo -n "mongodb+srv://exan_app:YOUR_DB_PASSWORD@exan-cluster-beta.xxxx.mongodb.net/exan?retryWrites=true&w=majority" | \
  gcloud secrets versions add MONGO_URI --data-file=-
```

---

## Official Documentation & References

- [MongoDB Atlas Getting Started Guide](https://www.mongodb.com/docs/atlas/getting-started/)
- [MongoDB Atlas Configure Database Users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/)
- [MongoDB Atlas IP Access Lists](https://www.mongodb.com/docs/atlas/security/ip-access-list/)
- [GCP Secret Manager Managing Secrets](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets)
