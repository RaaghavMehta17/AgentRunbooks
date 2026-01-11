import React, { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';

interface UsageMetrics {
  tokens_in: number;
  tokens_out: number;
  steps: number;
  adapter_calls: Record<string, number>;
  llm_cost: number;
  total_cost: number;
}

interface UsageData {
  tenant_id: string;
  range: string;
  start_date: string;
  end_date: string;
  usage: Array<{ day: string; metrics: UsageMetrics }>;
  totals: UsageMetrics;
}

interface QuotaInfo {
  warnings: Array<{ metric: string; period: string; limit: number; current: number }>;
  exceeded: Array<{ metric: string; period: string; limit: number; current: number }>;
  usage: {
    day: Record<string, number>;
    month: Record<string, number>;
  };
  limits: Record<string, Record<string, number>>;
}

interface Invoice {
  id: string;
  month: string;
  amount_usd: number;
  status: string;
  stripe_payment_link: string | null;
  created_at: string;
  paid_at: string | null;
}

export const Billing: React.FC = () => {
  const { token } = useAuth();
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [quotas, setQuotas] = useState<QuotaInfo | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBillingData();
  }, []);

  const fetchBillingData = async () => {
    try {
      const [usageRes, quotasRes, invoicesRes] = await Promise.all([
        fetch('/api/billing/usage?range=month', {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch('/api/billing/quotas', {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch('/api/billing/invoices', {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      if (usageRes.ok) {
        const usageData = await usageRes.json();
        setUsage(usageData);
      }

      if (quotasRes.ok) {
        const quotaData = await quotasRes.json();
        setQuotas(quotaData);
      }

      if (invoicesRes.ok) {
        const invoiceData = await invoicesRes.json();
        setInvoices(invoiceData.invoices || []);
      }
    } catch (error) {
      console.error('Failed to fetch billing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createStripeCustomer = async () => {
    try {
      const res = await fetch('/api/billing/stripe/create-customer', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        alert('Stripe customer created successfully');
      }
    } catch (error) {
      console.error('Failed to create Stripe customer:', error);
    }
  };

  const getQuotaPercentage = (metric: string, period: 'day' | 'month') => {
    if (!quotas) return 0;
    const usage_val = quotas.usage[period][metric] || 0;
    const limit = quotas.limits[metric]?.[`${period}_hard`] || 1;
    return Math.min((usage_val / limit) * 100, 100);
  };

  if (loading) {
    return <div>Loading billing data...</div>;
  }

  return (
    <div className="billing-container" style={{ padding: '2rem' }}>
      <h1>Billing & Usage</h1>

      {/* Usage Summary */}
      <section style={{ marginBottom: '2rem' }}>
        <h2>Current Month Usage</h2>
        {usage && (
          <div>
            <p>Total Tokens: {usage.totals.tokens_in + usage.totals.tokens_out}</p>
            <p>Steps Executed: {usage.totals.steps}</p>
            <p>Total Cost: ${usage.totals.total_cost.toFixed(2)}</p>
            <p>LLM Cost: ${usage.totals.llm_cost.toFixed(2)}</p>
          </div>
        )}
      </section>

      {/* Quota Status */}
      <section style={{ marginBottom: '2rem' }}>
        <h2>Quota Status</h2>
        {quotas && (
          <div>
            <h3>Daily Quotas</h3>
            {['tokens', 'cost', 'adapter_calls'].map((metric) => (
              <div key={metric} style={{ marginBottom: '1rem' }}>
                <label>{metric}</label>
                <div style={{ width: '100%', backgroundColor: '#e0e0e0', borderRadius: '4px', height: '20px' }}>
                  <div
                    style={{
                      width: `${getQuotaPercentage(metric, 'day')}%`,
                      backgroundColor: getQuotaPercentage(metric, 'day') > 80 ? '#ff9800' : '#4caf50',
                      height: '100%',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                <span>
                  {quotas.usage.day[metric] || 0} / {quotas.limits[metric]?.day_hard || 0}
                </span>
              </div>
            ))}

            <h3>Monthly Quotas</h3>
            {['tokens', 'cost', 'adapter_calls'].map((metric) => (
              <div key={metric} style={{ marginBottom: '1rem' }}>
                <label>{metric}</label>
                <div style={{ width: '100%', backgroundColor: '#e0e0e0', borderRadius: '4px', height: '20px' }}>
                  <div
                    style={{
                      width: `${getQuotaPercentage(metric, 'month')}%`,
                      backgroundColor: getQuotaPercentage(metric, 'month') > 80 ? '#ff9800' : '#4caf50',
                      height: '100%',
                      borderRadius: '4px',
                    }}
                  />
                </div>
                <span>
                  {quotas.usage.month[metric] || 0} / {quotas.limits[metric]?.month_hard || 0}
                </span>
              </div>
            ))}

            {quotas.warnings.length > 0 && (
              <div style={{ color: '#ff9800', marginTop: '1rem' }}>
                <strong>Warnings:</strong>
                <ul>
                  {quotas.warnings.map((w, i) => (
                    <li key={i}>
                      {w.metric} ({w.period}): {w.current} / {w.limit}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {quotas.exceeded.length > 0 && (
              <div style={{ color: '#f44336', marginTop: '1rem' }}>
                <strong>Exceeded:</strong>
                <ul>
                  {quotas.exceeded.map((e, i) => (
                    <li key={i}>
                      {e.metric} ({e.period}): {e.current} / {e.limit}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Invoices */}
      <section style={{ marginBottom: '2rem' }}>
        <h2>Invoice History</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>Month</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((invoice) => (
              <tr key={invoice.id}>
                <td>{invoice.month}</td>
                <td>${invoice.amount_usd.toFixed(2)}</td>
                <td>{invoice.status}</td>
                <td>
                  {invoice.status === 'pending' && invoice.stripe_payment_link && (
                    <a href={invoice.stripe_payment_link} target="_blank" rel="noopener noreferrer">
                      Pay
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Payment Method */}
      <section>
        <h2>Payment Method</h2>
        <button onClick={createStripeCustomer} style={{ padding: '0.5rem 1rem', marginTop: '1rem' }}>
          Add Payment Method (Test)
        </button>
        <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.5rem' }}>
          Note: This is test mode only. No real charges will be made.
        </p>
      </section>
    </div>
  );
};

