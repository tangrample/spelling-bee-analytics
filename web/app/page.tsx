import { getAnalytics } from '@/lib/analytics'
import Dashboard from '@/components/Dashboard'

export default async function Home() {
  const data = await getAnalytics()
  return <Dashboard data={data} />
}
