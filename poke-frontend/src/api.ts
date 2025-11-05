export type ApiError = Error & { status?: number; body?: string };

const API_BASE_URL = 'http://localhost:8000';

export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async ensureOk(response: Response, label: string): Promise<Response> {
    if (response.ok) {
      return response;
    }

    const body = await response.text().catch(() => '');
    const error = new Error(
      `${label}: ${response.status} ${response.statusText}`.trim(),
    ) as ApiError;
    error.status = response.status;
    error.body = body;
    throw error;
  }

  async createUser(connectionId: string, name?: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        connection_id: connectionId,
        name,
      }),
    });

    await this.ensureOk(response, 'Failed to create user');
    return response.json();
  }

  async getUser(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/users/${userId}`);
    await this.ensureOk(response, 'Failed to get user');
    return response.json();
  }

  async initiateConnection(userId: string, authConfigId?: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/connections/initiate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        auth_config_id: authConfigId,
      }),
    });

    await this.ensureOk(response, 'Failed to initiate connection');
    return response.json();
  }

  async checkConnectionStatus(connectionId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/connections/${connectionId}/status`);
    await this.ensureOk(response, 'Failed to check connection status');
    return response.json();
  }

  async sendMessage(userId: string, content: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        content,
      }),
    });

    await this.ensureOk(response, 'Failed to send message');
    return response.json();
  }

  async getMessageResponse(messageId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/messages/${messageId}/response`);
    await this.ensureOk(response, 'Failed to get message response');
    return response.json();
  }

  async getUserMemory(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/users/${userId}/memory`);
    await this.ensureOk(response, 'Failed to get user memory');
    return response.json();
  }

  async healthCheck(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health`);
    await this.ensureOk(response, 'Health check failed');
    return response.json();
  }

  async getUserConversations(userId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/users/${userId}/conversations`);
    await this.ensureOk(response, 'Failed to get conversations');
    return response.json();
  }
}

export const apiClient = new ApiClient();
