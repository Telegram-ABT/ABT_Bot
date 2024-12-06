from telebot import types

def create_info_menu(lang='en'):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    menu_buttons = {
        'ru': [
            ("📊 Стратегия", "strategy"),
            ("💱 Криптобиржи", "exchanges"),
            ("🔐 Безопасность", "security"),
            ("💰 Взаиморасчеты", "payments"),
            ("💎 Доп. доходы", "extraincome"),
            ("🔗 Как подключиться?", "howtoconnect"),
            ("⬅️ Назад", "back")
        ],
        'en': [
            ("📊 Strategy", "strategy"),
            ("💱 Crypto Exchanges", "exchanges"),
            ("🔐 Security", "security"),
            ("💰 Payments", "payments"),
            ("💎 Extra Income", "extraincome"),
            ("🔗 How to Connect?", "howtoconnect"),
            ("⬅️ Back", "back")
        ],
        'fra': [
            ("📊 Stratégie", "strategy"),
            ("💱 Exchanges Crypto", "exchanges"),
            ("🔐 Sécurité", "security"),
            ("💰 Paiements", "payments"),
            ("💎 Revenus Extras", "extraincome"),
            ("🔗 Comment se Connecter?", "howtoconnect"),
            ("⬅️ Retour", "back")
        ],
        'deu': [
            ("📊 Strategie", "strategy"),
            ("💱 Kryptobörsen", "exchanges"),
            ("🔐 Sicherheit", "security"),
            ("💰 Zahlungen", "payments"),
            ("💎 Zusätzliches Einkommen", "extraincome"),
            ("🔗 Wie verbinden?", "howtoconnect"),
            ("⬅️ Zurück", "back")
        ],
        'esp': [
            ("📊 Estrategia", "strategy"),
            ("💱 Exchanges de Cripto", "exchanges"),
            ("🔐 Seguridad", "security"),
            ("💰 Pagos", "payments"),
            ("💎 Ingresos Extra", "extraincome"),
            ("🔗 ¿Cómo Conectarse?", "howtoconnect"),
            ("⬅️ Volver", "back")
        ],
        'lang_zh': [
            ("📊 策略", "strategy"),
            ("💱 加密货币交易所", "exchanges"),
            ("🔐 安全", "security"),
            ("💰 支付", "payments"),
            ("💎 额外收入", "extraincome"),
            ("🔗 如何连接？", "howtoconnect"),
            ("⬅️ 返回", "back")
        ]
    }
    
    buttons = menu_buttons.get(lang, menu_buttons['en'])
    # Создаем все кнопки кроме последней (Назад) по две в ряд
    for i in range(0, len(buttons) - 1, 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(buttons) - 1:  # Проверяем, чтобы не добавить кнопку "Назад"
                text, callback = buttons[i + j]
                row_buttons.append(types.InlineKeyboardButton(text, callback_data=f"info_{callback}"))
        markup.row(*row_buttons)
    
    # Добавляем кнопку "Назад" отдельной строкой
    back_text, back_callback = buttons[-1]
    markup.row(types.InlineKeyboardButton(back_text, callback_data=f"info_{back_callback}"))
    
    return markup

def get_info_texts(lang='en'):
    info_texts_ru = {
            'menu_title': "Вы выбрали меню информация. Здесь вы можете ознакомиться с основной информацией:",
            'strategy': "<b>Описание стратегии:</b>\n\nLow risk стратегия 🛡️, которая сочетает элементы технического анализа 📊 и нейросеть AiBeTrade 🤖 для точного определения точек входа и выхода по более чем 20 валютным парам 💱.\n\nИсторические данные показывают отличные результаты 📈 — доходность за последний год составила 214.62% 🎯, при этом основное внимание уделяется снижению рисков ликвидации позиций ⚖️.\n\nПостоянный контроль эффективности стратегии позволяет стабильно сохранять и приумножать капитал 💰.",
            'exchanges': "<b>Поддерживаемые биржи:</b>\n\nBinance, Bybit, OKX, Bitget, BingX 🏦.\n\nРекомендуем использовать отдельный субаккаунт для автотрейдинга 🧩.",
            'security': "<b>1. Безопасность ваших финансов</b>\nВ режиме Автотрейдинг Про все средства находятся под вашим контролем и на вашем личном счете. Мы не имеем доступа к вашим деньгам и просто отправляем торговые сигналы по выбранной стратегии. Вы можете в любой момент приостановить операции или вывести средства — полная свобода действий.\n\n<b>2. Повышение доверия к сервису</b>\nВ режиме Автотрейдинг наши специалисты управляли вашими средствами напрямую, что могло вызывать сомнения у некоторых клиентов, хотя мы всегда действуем честно и прозрачно. Однако, признаем, что отсутствие контроля над собственными финансами — это потенциальный повод для недоверия. В Автотрейдинг Про таких рисков нет: все активы остаются под вашим полным управлением.\n\n<b>3. Прозрачность работы стратегии</b>\nКогда средства находятся на вашем счете, вы видите все транзакции в реальном времени. Мы будем публиковать отчеты и показывать общие результаты нашей работы, но кроме этого у каждого клиента всегда будет доступ к полной информации о наших действиях через свои подключенные через API аккаунты. Полная прозрачность — один из ключевых принципов Автотрейдинг Про.\n\n<b>4. Заинтересованность в результате</b>\nМы полностью отказались от абонентской платы и перешли на модель Share Profit, при которой наша прибыль напрямую зависит от ваших успехов. Чем лучше результаты торговли, тем больше заработают и клиенты, и мы. Это мотивирует нас работать максимально эффективно.",
            'payments': "<b>Взаиморасчеты и оплата услуг:</b>\n\nМы работаем по принципу Share Profit 💡 — зарабатываем только если зарабатываете вы! 💵\n\n<b>30%</b> от прибыли при депозите до <b>10K USD</b> 💼.\n\n<b>25%</b> от прибыли при депозите от <b>10K до 50K USD</b> 💰.\n\n<b>20%</b> от прибыли при депозите свыше <b>50K USD</b> 💎.\n\nВзаиморасчеты проводятся раз в квартал 🗓️ через перевод комиссии по указанным реквизитам 💳.",
            'extraincome': "🔔 <b>Зарабатывайте вместе с Autotrade PRO!</b> 🔔\n\nПриглашайте новых клиентов в наш сервис и получайте реферальное вознаграждение до 15% от суммы вознаграждения сервиса на протяжении всего времени, пока ваш приглашенный зарабатывает вместе с нами! 💰\n\n<b>Это отличная возможность как для вас, так и для ваших друзей:</b>\n\n- Клиенты зарабатывают на криптовалютных сделках с нашей стратегией 🔐📈\n\n- Вы стабильно получаете до 15% от их доходов на протяжении всего периода их работы с сервисом! 🚀\n\n<b>Не упустите шанс увеличить свои заработки вместе с Autotrade PRO!</b> 🎯",
            'howtoconnect': "<b>Процедура подключения:</b>\n\nДля подключения к Autotrade Pro необходимо предоставить данные API вашего аккаунта криптобиржи 🔐.\n\nВ настройках API биржи необходимо указать IP адреса наших серверов:\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\nМинимальная сумма депозита 1000 USDT\n\nЭто абсолютно безопасно ✅, так как у нас нет доступа к средствам 💵 — только к отправке торговых сигналов\n\nЕсли есть вопросы, то напишите в этом чат-боте 👇\n\n<b>Мы на связи по любым вопросам.</b>"
    }

    info_texts_en = {
            'menu_title': "You have selected the information menu. Here you can find the main information:",
            'strategy': "<b>Strategy Description:</b>\n\nLow risk strategy 🛡️, which combines elements of technical analysis 📊 and the AiBeTrade neural network 🤖 for precise determination of entry and exit points for more than 20 currency pairs 💱.\n\nHistorical data shows excellent results 📈 — the yield for the last year was 214.62% 🎯, while the main attention is paid to reducing the risks of liquidation of positions ⚖️.\n\nConstant monitoring of the strategy's effectiveness allows for stable preservation and growth of the capital 💰.",
            'exchanges': "<b>Supported Exchanges:</b>\n\nBinance, Bybit, OKX, Bitget, BingX 🏦.\n\nWe recommend using a separate subaccount for autotrading 🧩.",
            'security': "<b>1. Financial Security</b>\n\nIn the Autotrading PRO mode, all funds are under your control and on your personal account. We do not have access to your funds and simply send trading signals according to the selected strategy. You can pause operations or withdraw funds at any time — full freedom of action.\n\n<b>2. Increasing Trust in the Service</b>\nIn the Autotrading mode, our specialists managed your funds directly, which could cause doubts among some clients, although we always act honestly and transparently. However, we admit that the lack of control over your own finances is a potential reason for distrust. In Autotrading PRO, there are no such risks: all assets remain under your full control.\n\n<b>3. Transparency of Strategy Work</b>\nWhen funds are on your account, you see all transactions in real time. We will publish reports and show general results of our work, but in addition, each client will always have access to full information about our actions through their connected through API accounts. Full transparency is one of the key principles of Autotrading PRO.\n\n<b>4. Interest in Results</b>\nWe completely abandoned the subscription fee and switched to the Share Profit model, where our profit directly depends on your success. The better the trading results, the more both clients and we earn. This motivates us to work as efficiently as possible.",
            'payments': "<b>Payments and Service Fees:</b>\n\nWe work on the Share Profit principle 💡 — we only earn if you earn! 💵\n\n<b>30%</b> from the profit at a deposit of up to <b>10K USD</b> 💼.\n\n<b>25%</b> from the profit at a deposit from <b>10K to 50K USD</b> 💰.\n\n<b>20%</b> from the profit at a deposit of more than <b>50K USD</b> 💎.\n\nPayments are made once every quarter 🗓️ via the commission transfer to the specified details 💳.",
            'extraincome': "🔔 <b>Earn with Autotrade PRO!</b>\n\nInvite new clients to our service and receive a referral reward of up to 15% of the service's reward amount for the entire period, while your invited client earns with us! 💰\n\n<b>This is a great opportunity both for you and for your friends:</b>\n\n- Clients earn on cryptocurrency deals with our strategy 🔐📈\n\n- You consistently receive up to 15% of their earnings for the entire period of their work with the service! 🚀\n\n<b>Don't miss the chance to increase your earnings together with Autotrade PRO!</b> 🎯",
            'howtoconnect': "<b>Connection Procedure:</b>\n\nTo connect to Autotrade Pro, you need to provide the API data of your cryptocurrency exchange account 🔐.\n\nIn the API settings of the exchange, you need to specify the IP addresses of our servers:\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\nMinimum deposit amount is 1000 USDT\n\nThis is absolutely safe ✅, since we do not have access to your funds 💵 — only to sending trading signals\n\nIf you have any questions, write to this chatbot 👇\n\n<b>We are available for any questions.</b>"
    }
    info_texts_fra = {
            'menu_title': "Vous avez sélectionné le menu d'information. Voici les informations principales :",
            'strategy': "<b>Description de la Stratégie:</b>\n\nStratégie de faible risque 🛡️, qui combine des éléments d'analyse technique 📊 et le réseau neuronal AiBeTrade 🤖 pour déterminer avec précision les points d'entrée et de sortie pour plus de 20 paires de devises 💱.\n\nLes données historiques montrent des résultats excellents 📈 — le rendement pour l'année dernière a été de 214,62% 🎯, tandis que l'attention principale est portée sur la réduction des risques de liquidation des positions ⚖️.\n\nLe suivi constant de l'efficacité de la stratégie permet de préserver et de faire croître le capital de manière stable 💰.",
            'exchanges': "<b>Exchanges Supportés:</b>\n\nBinance, Bybit, OKX, Bitget, BingX 🏦.\n\nNous recommandons d'utiliser un sous-compte séparé pour l'autotrading 🧩.",
            'security': "<b>1. Sécurité Financière</b>\n\nDans le mode Autotrading PRO, tous les fonds sont sous votre contrôle et sur votre compte personnel. Nous n'avons pas accès à vos fonds et envoyons simplement des signaux de trading en fonction de la stratégie choisie. Vous pouvez interrompre les opérations ou retirer des fonds à tout moment — pleine liberté d'action.\n\n<b>2. Augmentation de la Confiance dans le Service</b>\nDans le mode Autotrading, nos spécialistes ont géré vos fonds directement, ce qui pourrait susciter des doutes parmi certains clients, bien que nous agissions toujours avec honnêteté et transparence. Cependant, nous reconnaissons que le manque de contrôle sur vos propres finances est un potentiel motif de défiance. Dans Autotrading PRO, il n'existe aucun tel risque : tous les actifs restent sous votre contrôle total.\n\n<b>3. Transparence du Fonctionnement de la Stratégie</b>\nLorsque les fonds sont sur votre compte, vous voyez toutes les transactions en temps réel. Nous publierons des rapports et montrerons les résultats globaux de notre travail, mais en plus, chaque client aura toujours accès à l'information complète sur nos actions via ses comptes connectés via API.\n\nLa transparence totale est l'un des principes clés de Autotrading PRO.",
            'payments': "<b>Calculs réciproques et paiement des services :</b>\n\nNous travaillons selon le principe du Share Profit 💡 — nous gagnons seulement si vous gagnez ! 💵\n\n<b>30%</b> des bénéfices pour un dépôt jusqu'à <b>10K USD</b> 💼.\n\n<b>25%</b> des bénéfices pour un dépôt de <b>10K à 50K USD</b> 💰.\n\n<b>20%</b> des bénéfices pour un dépôt supérieur à <b>50K USD</b> 💎.\n\nLes calculs réciproques sont effectués chaque trimestre 🗓️ par transfert de commission aux coordonnées indiquées 💳.",
            'extraincome': "🔔 <b>Gagnez avec Autotrade PRO!</b>\n\nInvitez de nouveaux clients à notre service et recevez une récompense de parrainage de jusqu'à 15% du montant de la récompense du service pour la période entière, tandis que votre client invité gagne avec nous! 💰\n\n<b>C'est une excellente opportunité pour vous et pour vos amis :</b>\n\n- Les clients gagnent sur les transactions en crypto avec notre stratégie 🔐📈\n\n- Vous recevez jusqu'à 15% de leurs gains pour la période entière de leur travail avec le service! 🚀\n\n<b>Ne manquez pas l'opportunité d'augmenter vos gains ensemble avec Autotrade PRO!</b> 🎯",
            'howtoconnect': "<b>Procédure de connexion :</b>\n\nPour vous connecter à Autotrade Pro, vous devez fournir les données API de votre compte d'échange de crypto-monnaies 🔐.\n\nDans les paramètres API de l'échange, vous devez spécifier les adresses IP de nos serveurs :\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\nMontant minimum du dépôt est de 1000 USDT\n\nC'est absolument sécurisé ✅, car nous n'avons pas accès aux fonds 💵 — seulement à l'envoi de signaux de trading\n\nSi vous avez des questions, écrivez dans ce chat-bot 👇\n\n<b>Nous sommes disponibles pour toute question.</b>"            
    }
    info_texts_deu = {
            'menu_title': "Sie haben das Informationsmenü ausgewählt. Hier finden Sie die wichtigsten Informationen:",
            'strategy': "<b>Strategiebeschreibung:</b>\n\nNiedrigrisiko-Strategie 🛡️, die Elemente der technischen Analyse 📊 und das AiBeTrade-Neuronale Netzwerk 🤖 kombiniert, um präzise Einstiegs- und Ausstiegspunkte für mehr als 20 Währungspaare 💱 zu bestimmen.\n\nHistorische Daten zeigen hervorragende Ergebnisse 📈 — die Rendite im letzten Jahr betrug 214,62% 🎯, wobei besonderes Augenmerk auf die Reduzierung der Risiken der Liquidation von Positionen ⚖️ gelegt wird.\n\nDurch ständige Überwachung der Effektivität der Strategie wird eine stabile Erhaltung und Wachstum des Kapitals 💰 ermöglicht.",
            'exchanges': "<b>Unterstützte Börsen:</b>\n\nBinance, Bybit, OKX, Bitget, BingX 🏦.\n\nWir empfehlen die Verwendung eines separaten Unterkontos für den Autohandel 🧩.",
            'security': "<b>1. Sicherheit Ihrer Finanzen</b>\n\nIm Modus Autotrading Pro befinden sich alle Mittel unter Ihrer Kontrolle und auf Ihrem persönlichen Konto. Wir haben keinen Zugriff auf Ihr Geld und senden lediglich Handelssignale gemäß der gewählten Strategie. Sie können jederzeit die Operationen pausieren oder Gelder abheben — volle Handlungsfreiheit.\n\n<b>2. Erhöhung des Vertrauens in den Service</b>\n\nIm Modus Autotrading verwalteten unsere Spezialisten Ihre Mittel direkt, was bei einigen Kunden Zweifel hervorrufen konnte, obwohl wir immer ehrlich und transparent gehandelt haben. Wir erkennen jedoch an, dass der Mangel an Kontrolle über die eigenen Finanzen ein potenzieller Grund für Misstrauen ist. Im Autotrading Pro gibt es solche Risiken nicht: Alle Vermögenswerte bleiben unter Ihrer vollen Kontrolle.\n\n<b>3. Transparenz der Strategiearbeit</b>\n\nWenn die Mittel auf Ihrem Konto sind, sehen Sie alle Transaktionen in Echtzeit. Wir werden Berichte veröffentlichen und die allgemeinen Ergebnisse unserer Arbeit zeigen, aber darüber hinaus hat jeder Kunde jederzeit Zugang zu vollständiger Information über unsere Aktionen durch seine über API verbundenen Konten. Volle Transparenz ist eines der Schlüsselprinzipien von Autotrading Pro.\n\n<b>4. Interesse am Ergebnis</b>\n\nWir haben vollständig auf die Abonnementgebühr verzichtet und sind auf das Modell Share Profit umgestiegen, bei dem unser Gewinn direkt von Ihrem Erfolg abhängt. Je besser die Handelsergebnisse, desto mehr verdienen sowohl die Kunden als auch wir. Das motiviert uns, so effektiv wie möglich zu arbeiten.",
            'payments': "<b>Abrechnungen und Bezahlung von Dienstleistungen:</b>\n\nWir arbeiten nach dem Share-Profit-Prinzip 💡 — wir verdienen nur, wenn Sie verdienen! 💵\n\n<b>30%</b> vom Gewinn bei einer Einzahlung bis zu <b>10K USD</b> 💼.\n\n<b>25%</b> vom Gewinn bei einer Einzahlung von <b>10K bis 50K USD</b> 💰.\n\n<b>20%</b> vom Gewinn bei einer Einzahlung über <b>50K USD</b> 💎.\n\nDie Abrechnungen erfolgen vierteljährlich 🗓️ durch die Überweisung der Provision auf die angegebenen Kontodaten 💳.",
            'extraincome': "🔔 <b>Verdienen Sie mit Autotrade PRO!</b>\n\nInvitez de nouveaux clients à notre service et recevez une récompense de parrainage de jusqu'à 15% du montant de la récompense du service pour la période entière, tandis que votre client invité gagne avec nous! 💰\n\n<b>C'est une excellente opportunité pour vous et pour vos amis :</b>\n\n- Les clients gagnent sur les transactions en crypto avec notre stratégie 🔐📈\n\n- Vous recevez jusqu'à 15% de leurs gains pour la période entière de leur travail avec le service! 🚀\n\n<b>Ne manquez pas l'opportunité d'augmenter vos gains ensemble avec Autotrade PRO!</b> 🎯",
            'howtoconnect': "<b>Verbindungsverfahren:</b>\n\nUm eine Verbindung zu Autotrade Pro herzustellen, müssen Sie die API-Daten Ihres Kryptowährungsbörsenkontos bereitstellen 🔐.\n\nIn den API-Einstellungen der Börse müssen Sie die IP-Adressen unserer Server angeben:\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\nDer Mindestbetrag für die Einzahlung beträgt 1000 USDT\n\nDas ist absolut sicher ✅, da wir keinen Zugriff auf Gelder 💵 haben — nur auf das Senden von Handelssignalen.\n\nWenn Sie Fragen haben, schreiben Sie in diesem Chat-Bot 👇\n\n<b>Wir sind für alle Fragen erreichbar.</b>"            
    }
    info_texts_esp = {
            'menu_title': "Has seleccionado el menú de información. Aquí puedes encontrar la información principal:",
            'strategy': "<b>Descripción de la Estrategia:</b>\n\nEstrategia de bajo riesgo 🛡️, que combina elementos de análisis técnico 📊 y la red neuronal AiBeTrade 🤖 para determinar con precisión los puntos de entrada y salida para más de 20 pares de divisas 💱.\n\nLos datos históricos muestran resultados excelentes 📈 — el rendimiento del último año fue del 214,62% 🎯, mientras que la atención principal se centra en la reducción de los riesgos de liquidación de posiciones ⚖️.\n\nEl seguimiento constante de la efectividad de la estrategia permite una preservación y crecimiento estable del capital 💰.",
            'exchanges': "<b>Exchanges Soportados:</b>\n\nBinance, Bybit, OKX, Bitget, BingX 🏦.\n\nRecomendamos usar una subcuenta separada para el autotrading 🧩.",
            'security': "<b>1. Seguridad Financiera</b>\n\nEn el modo Autotrading PRO, todos los fondos están bajo su control y en su cuenta personal. No tenemos acceso a sus fondos y simplemente enviamos señales de trading según la estrategia seleccionada. Puede pausar las operaciones o retirar fondos en cualquier momento — plena libertad de acción.\n\n<b>2. Incremento de la Confianza en el Servicio</b>\nEn el modo Autotrading, nuestros especialistas gestionaron sus fondos directamente, lo que podría causar dudas entre algunos clientes, aunque siempre actuamos con honestidad y transparencia. Sin embargo, reconocemos que el ausente control sobre sus propios fondos es una potencial razón para la desconfianza. En Autotrading PRO, no existen tales riesgos: todos los activos permanecen bajo su control total.\n\n<b>3. Transparencia del Funcionamiento de la Estrategia</b>\nCuando los fondos están en su cuenta, puede ver todas las transacciones en tiempo real. Publicaremos informes y mostraremos los resultados generales de nuestro trabajo, pero además, cada cliente siempre tendrá acceso a la información completa sobre nuestras acciones a través de sus cuentas conectadas a través de API.\n\nLa transparencia total es uno de los principios clave de Autotrading PRO.\n\n<b>4. Interés en los Resultados</b>\nNos hemos desvinculado por completo de la tarifa de suscripción y nos hemos trasladado al modelo Share Profit, en el que nuestro beneficio directamente depende de sus éxitos. Cuanto mejor sean los resultados del trading, más ganarán tanto los clientes como nosotros. Esto nos motiva a trabajar lo más eficientemente posible.",
            'payments': "<b>Reconciliaciones y pago de servicios:</b>\n\n¡Trabajamos bajo el principio de Share Profit 💡 — solo ganamos si tú ganas! 💵\n\n<b>30%</b> de las ganancias con un depósito de hasta <b>10K USD</b> 💼.\n\n<b>25%</b> de las ganancias con un depósito de <b>10K a 50K USD</b> 💰.\n\n<b>20%</b> de las ganancias con un depósito superior a <b>50K USD</b> 💎.\n\nLas reconciliaciones se realizan trimestralmente 🗓️ mediante transferencia de comisión a los datos indicados 💳.",
            'extraincome': "🔔 <b>¡Gana con Autotrade PRO!</b>\n\nInvitez de nouveaux clients à notre service et recevez une récompense de parrainage de jusqu'à 15% du montant de la récompense du service pour la période entière, tandis que votre client invité gagne avec nous! 💰\n\n<b>C'est une excellente opportunité pour vous et pour vos amis :</b>\n\n- Les clients gagnent sur les transactions en crypto avec notre stratégie 🔐📈\n\n- Vous recevez jusqu'à 15% de leurs gains pour la période entière de leur travail avec le service! 🚀\n\n<b>Ne manquez pas l'opportunité d'augmenter vos gains ensemble avec Autotrade PRO!</b> 🎯",
            'howtoconnect': "<b>Procedimiento de conexión:</b>\n\nPara conectarse a Autotrade Pro, es necesario proporcionar los datos API de su cuenta de criptobolsa 🔐.\n\nEn la configuración de la API de la bolsa, debe especificar las direcciones IP de nuestros servidores:\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\nLa cantidad mínima de depósito es 1000 USDT\n\nEsto es absolutamente seguro ✅, ya que no tenemos acceso a los fondos 💵 — solo al envío de señales de trading.\n\nSi tiene preguntas, escríbanos en este chat-bot 👇\n\n<b>Estamos disponibles para cualquier consulta.</b>"            
    }
    info_texts_zh = {
            'menu_title': "您已选择信息菜单。在这里您可以找到主要信息：",
            'strategy': "<b>策略说明:</b>\n\n低风险策略 🛡️，结合技术分析 📊 和 AiBeTrade 神经网络 🤖 以精确确定超过 20 种货币对的入场和出场点 💱。\n\n历史数据显示出色结果 📈 — 去年回报率为 214.62% 🎯，同时主要关注降低仓位清算风险 ⚖️。\n\n通过持续监控策略的有效性，可以稳定保持和增长资本 💰。",
            'security': "<b>1. 财务安全</b>\n\n在 Autotrading PRO 模式下，所有资金都在您的控制之下，并位于您的个人账户中。我们无法访问您的资金，只是根据您选择策略发送交易信号。您可以随时暂停操作或提取资金 — 完全自由行动。\n\n<b>2. 增加对服务的信任</b>\n在 Autotrading 模式下，我们的专家直接管理您的资金，这可能会让一些客户产生怀疑，尽管我们始终诚实和透明地行事。然而，我们承认，缺乏对自己财务的控制是潜在的不信任原因。在 Autotrading PRO 中，不存在此类风险：所有资产都保持在您的完全控制之下。\n\n<b>3. 策略工作透明度</b>\n当资金在您的账户中时，您可以实时看到所有交易。我们将发布报告并展示我们工作的总体结果，但除此之外，每个客户始终可以通过其通过 API 连接的账户访问有关我们行动的完整信息。完全透明是 Autotrading PRO 的关键原则之一。\n\n<b>4. 对结果的兴趣</b>\n我们完全放弃了订阅费，转而采用 Share Profit 模型，在这种模型中，我们的利润直接取决于您的成功。交易结果越好，客户和我们都赚得越多。这激励我们尽可能高效地工作。",
            'payments': "<b>支付和服务费用：</b>\n\n我们遵循 Share Profit 原则 💡 — 我们只赚取利润，如果您赚取利润！ 💵\n\n<b>30%</b> 的利润，当存款不超过 <b>10K USD</b> 💼。\n\n<b>25%</b> 的利润，当存款在 <b>10K 到 50K USD</b> 之间 💰。\n\n<b>20%</b> 的利润，当存款超过 <b>50K USD</b> 💎。\n\n每季度结算 🗓️ 通过手续费转账到指定账户 💳。",
            'extraincome': "🔔 <b>与 Autotrade PRO 一起赚钱</b>\n\n邀请新客户到我们的服务，并获得高达 15% 的服务奖励的推荐奖励，而您的推荐客户与我们一起赚钱！ 💰\n\n<b>这是一个很好的机会，既对你自己，也对你的朋友：</b>\n\n- 客户通过我们的策略在加密货币交易中赚钱 🔐📈\n\n- 您可以获得高达 15% 的推荐客户在服务期间赚取的利润！ 🚀\n\n<b>不要错过与 Autotrade PRO 一起增加您的收入的机会！</b> 🎯",
            'howtoconnect': "<b>连接程序：</b>\n\n要连接到 Autotrade Pro，需要提供您加密货币交易所账户的 API 数据 🔐。\n\n在交易所的 API 设置中，必须指定我们服务器的 IP 地址：\n\n<code>5.181.20.47,146.19.196.69,91.194.160.154,209.38.243.235</code>\n\n最低存款额为 1000 USDT\n\n这是绝对安全的 ✅，因为我们无法访问您的资金 💵 — 只是发送交易信号。\n\n如果您有任何问题，请给我们写信 👇\n\n<b>我们随时为您服务。</b>"
    }    
   
    if lang == 'ru':
        return info_texts_ru
    elif lang == 'fra':
        return info_texts_fra
    elif lang == 'deu':
        return info_texts_deu
    elif lang == 'esp':
        return info_texts_esp
    elif lang == 'lang_zh':
        return info_texts_zh
    else:
        return info_texts_en

def handle_info_section(bot, message, lang, section):
    """
    Обработчик для разделов информационного меню
    """
    # try:
        # Получаем тексты для выбранного языка
    texts = get_info_texts(lang)
    
    # Если это кнопка "назад", возвращаемся в главное меню
    if section == "back":
        return "back"
        
    if section == "info_extraincome":
        section_text = texts.get("extraincome")
        return section_text
    elif section == "info_howtoconnect":
        section_text = texts.get('howtoconnect')
        return section_text
    else:
        # Получаем текст для выбранного раздела
        section_text = texts.get(section, "Information not available")
    # Отправляем сообщение с информацией и меню
    bot.send_message(
        message.chat.id,
        section_text,
        parse_mode='HTML',
        reply_markup=create_info_menu(lang)
    )
    
    return "info_sent"
        
    # except Exception as e:
    #     print(f"Error in handle_info_section: {str(e)}")
    #     return "error"
    # poetry run python bits_support.py