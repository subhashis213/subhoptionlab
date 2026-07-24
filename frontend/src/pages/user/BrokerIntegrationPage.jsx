import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import BrokerConnect from '../../components/BrokerConnect'

export default function BrokerIntegrationPage() {
  const navigate = useNavigate()

  return (
    <div className="page broker-integration-page pb-20">
      {/* Header with Back Button */}
      <div className="nav-header-bar">
        <button className="btn-back-icon" onClick={() => navigate('/profile')}>
          <ArrowLeft size={20} />
        </button>
        <h2>Broker Setup</h2>
      </div>

      <div className="container-padding" style={{ marginTop: '20px' }}>
        <BrokerConnect />
      </div>
    </div>
  )
}
