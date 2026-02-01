from sqlalchemy.orm import Session
from app.db.models.risk_snapshot import RiskSnapshot
from app.db.models.career import CareerProfile

class BenchmarkEngine:

    def compute(self, db: Session, user):
        # 1. Recupera o perfil para segmentação
        profile = user.career_profile
        if not profile:
            return None

        # 2. Recupera o snapshot mais recente do usuário
        latest = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.user_id == user.id)
            .order_by(RiskSnapshot.recorded_at.desc())
            .first()
        )
        if not latest:
            return None

        # 3. Busca pares (Segmentação: Mesma Senioridade e Stack)
        # Nota: Limitamos a 1000 para performance
        peers = (
            db.query(RiskSnapshot.risk_score)
            .join(CareerProfile, CareerProfile.user_id == RiskSnapshot.user_id)
            .filter(CareerProfile.seniority == profile.seniority)
            .filter(CareerProfile.primary_stack == profile.primary_stack)
            .order_by(RiskSnapshot.recorded_at.desc())
            .limit(1000)
            .all()
        )

        context_label = f"{profile.seniority} {profile.primary_stack} Developers"

        # 4. Fallback: Se não houver dados de pares suficientes (< 5), usa Global
        if not peers or len(peers) < 5:
            peers = (
                db.query(RiskSnapshot.risk_score)
                .order_by(RiskSnapshot.recorded_at.desc())
                .limit(1000)
                .all()
            )
            context_label = "Global Developer Market"

        if not peers:
            return None

        # 5. Cálculo do Percentil
        # peers é uma lista de tuplas (score,), por isso usamos p[0]
        scores = sorted([p[0] for p in peers])
        
        # Percentil: Quantos % são 'piores' (risco maior) ou iguais ao meu?
        # Aqui invertemos a lógica típica de 'safer':
        # Se meu risco é baixo (ex: 20), e a maioria é 80, estou 'safer than' muitos.
        # Risco menor = Melhor.
        
        # Quantas pessoas têm risco MAIOR ou IGUAL ao meu? (Estou melhor que elas)
        better_than_count = sum(1 for s in scores if s >= latest.risk_score)
        percentile = int((better_than_count / len(scores)) * 100)

        return {
            "user_risk": latest.risk_score,
            "context": context_label,
            "percentile": percentile,
            "message": (
                f"Compared to {context_label}, you are safer than "
                f"{percentile}% of them."
            )
        }


benchmark_engine = BenchmarkEngine()
