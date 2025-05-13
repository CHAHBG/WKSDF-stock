import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import io
import hashlib

st.set_page_config(page_title="WKSDF Stock", layout="wide")

# Chemin vers le fichier Excel
excel_path = "data/stock_data.xlsx"
users_path = "data/users.csv"

# Vérifier si le répertoire data existe, sinon le créer
if not os.path.exists("data"):
    os.makedirs("data")


# Gestion des utilisateurs
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_users():
    if not os.path.exists(users_path):
        users_df = pd.DataFrame([
            {"username": "admin", "password": hash_password("Samayaye67"), "role": "admin"},
            {"username": "user", "password": hash_password("Wksdfuser0525"), "role": "user"}
        ])
        users_df.to_csv(users_path, index=False)
    return pd.read_csv(users_path)


def authenticate(username, password):
    users_df = init_users()
    user_row = users_df[users_df["username"] == username]
    if not user_row.empty:
        stored_password = user_row.iloc[0]["password"]
        if stored_password == hash_password(password):
            return user_row.iloc[0]["role"]
    return None


# Chargement des données
def load_data():
    if os.path.exists(excel_path):
        produits = pd.read_excel(excel_path, sheet_name="Produits")
        mouvements = pd.read_excel(excel_path, sheet_name="Mouvements")
    else:
        produits = pd.DataFrame(
            columns=["ID", "Nom Produit", "Catégorie", "Prix Unitaire", "Quantité", "Seuil Alerte", "Date Ajout"])
        mouvements = pd.DataFrame(columns=["ID", "Date", "Produit", "Type", "Quantité", "Commentaire"])
    return produits, mouvements


# Sauvegarde des données
def save_data(produits, mouvements):
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="w") as writer:
        produits.to_excel(writer, sheet_name="Produits", index=False)
        mouvements.to_excel(writer, sheet_name="Mouvements", index=False)


# Réinitialisation du stock
def initialiser_stock():
    produits_df = st.session_state.produits_df.copy()
    produits_df["Quantité"] = 0
    st.session_state.produits_df = produits_df
    save_data(produits_df, st.session_state.mouvements_df)
    st.success("✅ Le stock a été réinitialisé avec succès.")


# Purger toutes les données
def purger_donnees():
    st.session_state.produits_df = pd.DataFrame(
        columns=["ID", "Nom Produit", "Catégorie", "Prix Unitaire", "Quantité", "Seuil Alerte", "Date Ajout"])
    st.session_state.mouvements_df = pd.DataFrame(columns=["ID", "Date", "Produit", "Type", "Quantité", "Commentaire"])
    save_data(st.session_state.produits_df, st.session_state.mouvements_df)
    st.success("✅ Toutes les données ont été purgées avec succès.")


# Calculer les recettes par période
def calculer_recettes(mouvements_df, produits_df, periode='jour'):
    if mouvements_df.empty:
        return pd.DataFrame(columns=["Période", "Recettes"])

    # S'assurer que la date est au bon format
    mouvements_df["Date"] = pd.to_datetime(mouvements_df["Date"])

    # Filtrer uniquement les sorties
    sorties_df = mouvements_df[mouvements_df["Type"] == "Sortie"].copy()

    # Ajouter une colonne pour le prix
    sorties_df["Prix Unitaire"] = sorties_df.apply(
        lambda row: produits_df.loc[produits_df["Nom Produit"] == row["Produit"], "Prix Unitaire"].values[0]
        if not produits_df.loc[produits_df["Nom Produit"] == row["Produit"], "Prix Unitaire"].empty else 0,
        axis=1
    )

    # Calculer le montant
    sorties_df["Montant"] = sorties_df["Quantité"] * sorties_df["Prix Unitaire"]

    # Grouper selon la période
    if periode == 'jour':
        sorties_df["Période"] = sorties_df["Date"].dt.date
    elif periode == 'mois':
        sorties_df["Période"] = sorties_df["Date"].dt.to_period("M").dt.to_timestamp()
    elif periode == 'année':
        sorties_df["Période"] = sorties_df["Date"].dt.year

    # Grouper et calculer la somme
    recettes_df = sorties_df.groupby("Période")["Montant"].sum().reset_index()
    recettes_df.rename(columns={"Montant": "Recettes"}, inplace=True)

    return recettes_df


# Export des données en Excel
def export_excel(produits_df, mouvements_df, recettes_df=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        produits_df.to_excel(writer, sheet_name="Produits", index=False)
        mouvements_df.to_excel(writer, sheet_name="Mouvements", index=False)
        if recettes_df is not None:
            recettes_df.to_excel(writer, sheet_name="Recettes", index=False)

    return output.getvalue()


# Initialisation session_state
if "produits_df" not in st.session_state or "mouvements_df" not in st.session_state:
    st.session_state.produits_df, st.session_state.mouvements_df = load_data()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None

# Système d'authentification
if not st.session_state.authenticated:
    st.title("📦 Wakeur Sokhna Daba Falilou - Connexion")

    col1, col2 = st.columns([1, 2])

    with col1:
        # Vérifier si le logo existe, sinon utiliser une image par défaut
        if os.path.exists("logo/wksdf.png"):
            st.image("logo/wksdf.png", width=150)
        else:
            # Créer le répertoire logo s'il n'existe pas
            if not os.path.exists("logo"):
                os.makedirs("logo")
            st.warning("Logo non trouvé. Veuillez placer votre logo à 'logo/wksdf.png'")
            st.image("https://www.svgrepo.com/show/526049/security-safe.svg", width=150)

    with col2:
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")

        login_button = st.button("Connexion")

        if login_button:
            role = authenticate(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.role = role
                st.success(f"✅ Bienvenue {username} ! Vous êtes connecté en tant que {role}.")
                st.rerun()
            else:
                st.error("❌ Nom d'utilisateur ou mot de passe incorrect.")

    st.markdown("---")
    st.info("Veuillez vous connecter pour accéder à l'application de gestion de stock.")

    st.stop()

# Titre principal après authentification
st.title("📦 Wakeur Sokhna Daba Faliou - Gestion de Stock")
st.sidebar.success(f"👤 Connecté en tant que: {st.session_state.role.upper()}")

# Bouton de déconnexion
if st.sidebar.button("🔒 Déconnexion"):
    st.session_state.authenticated = False
    st.session_state.role = None
    st.rerun()

# Menu latéral
if st.session_state.role == "admin":
    menu = st.sidebar.radio("Navigation", ["📊 Tableau de bord", "📦 Produits", "➕ Entrée / ➖ Sortie", "📁 Exportation",
                                           "⚙️ Réinitialiser Stock"])
else:
    menu = st.sidebar.radio("Navigation", ["📊 Tableau de bord", "📦 Produits", "➕ Entrée / ➖ Sortie", "📁 Exportation"])

# Onglet Tableau de bord
if menu == "📊 Tableau de bord":
    st.header("📊 Tableau de bord")
    produits_df = st.session_state.produits_df
    mouvements_df = st.session_state.mouvements_df

    total_articles = produits_df["Quantité"].sum()
    nb_produits = produits_df.shape[0]
    produits_alerte = produits_df[produits_df["Quantité"] <= produits_df["Seuil Alerte"]]

    recettes = 0
    for _, row in mouvements_df[mouvements_df["Type"] == "Sortie"].iterrows():
        prix = produits_df.loc[produits_df["Nom Produit"] == row["Produit"], "Prix Unitaire"]
        if not prix.empty:
            recettes += prix.values[0] * row["Quantité"]

    col1, col2, col3 = st.columns(3)
    col1.metric("🔢 Nombre de produits", nb_produits)
    col2.metric("📦 Stock total", total_articles)
    col3.metric("💰 Recettes générées", f"{recettes:.0f} FCFA")

    if not produits_alerte.empty:
        st.warning("⚠️ Produits en dessous du seuil d'alerte :")
        st.dataframe(produits_alerte)

    # Options d'affichage des graphiques
    st.subheader("📊 Analyse graphique")

    # Graphique par catégorie
    if not produits_df.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Répartition par catégorie")
            cat_data = produits_df.groupby("Catégorie")["Quantité"].sum().reset_index()
            if not cat_data.empty:
                fig_cat = px.pie(cat_data, names="Catégorie", values="Quantité",
                                 title="Répartition des produits par catégorie")
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("Aucune donnée de catégorie disponible")

        with col2:
            st.subheader("Top produits en stock")
            top_produits = produits_df.nlargest(5, "Quantité")
            if not top_produits.empty:
                fig_top = px.bar(top_produits, x="Nom Produit", y="Quantité", title="Top 5 des produits en stock")
                st.plotly_chart(fig_top, use_container_width=True)
            else:
                st.info("Aucun produit en stock")

    # Détail des produits par catégorie
    if not produits_df.empty:
        st.subheader("📊 Produits par catégorie")

        categories = produits_df["Catégorie"].unique()
        if len(categories) > 0:
            selected_cat = st.selectbox("Sélectionner une catégorie", categories)

            cat_products = produits_df[produits_df["Catégorie"] == selected_cat]
            if not cat_products.empty:
                fig_cat_detail = px.bar(cat_products,
                                        x="Nom Produit",
                                        y="Quantité",
                                        color="Prix Unitaire",
                                        title=f"Produits dans la catégorie: {selected_cat}",
                                        color_continuous_scale="Viridis")

                st.plotly_chart(fig_cat_detail, use_container_width=True)

                # Afficher les infos sur les produits de cette catégorie
                col1, col2, col3 = st.columns(3)
                col1.metric("Nombre de produits", len(cat_products))
                col2.metric("Quantité totale", cat_products["Quantité"].sum())
                col3.metric("Valeur totale",
                            f"{(cat_products['Quantité'] * cat_products['Prix Unitaire']).sum():.0f} FCFA")

                # Afficher le tableau des produits de cette catégorie
                st.dataframe(cat_products[["Nom Produit", "Quantité", "Prix Unitaire", "Seuil Alerte"]])
            else:
                st.info(f"Aucun produit dans la catégorie {selected_cat}")
        else:
            st.info("Aucune catégorie disponible")

    # Graphique recettes
    st.subheader("📈 Analyse des recettes")

    periode = st.selectbox("Sélectionnez la période d'analyse", ["jour", "mois", "année"])

    recettes_df = calculer_recettes(mouvements_df, produits_df, periode)

    if not recettes_df.empty:
        fig_recettes = px.line(recettes_df, x="Période", y="Recettes",
                               title=f"Évolution des recettes par {periode}")
        st.plotly_chart(fig_recettes)

        # Export des recettes
        export_recettes = export_excel(produits_df, mouvements_df, recettes_df)
        st.download_button(
            label=f"📥 Exporter les recettes par {periode} (Excel)",
            data=export_recettes,
            file_name=f"recettes_par_{periode}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info(f"Aucune donnée de recette disponible par {periode}")

    # Graphique évolution mouvements
    if not mouvements_df.empty:
        st.subheader("📊 Évolution des mouvements")
        mouvements_df["Date"] = pd.to_datetime(mouvements_df["Date"])
        periode_mvt = st.selectbox("Sélectionnez la période pour les mouvements", ["jour", "mois", "année"],
                                   key="select_periode_mvt")

        if periode_mvt == "jour":
            mouvements_grouped = mouvements_df.groupby([mouvements_df["Date"].dt.date, "Type"])[
                "Quantité"].sum().reset_index()
        elif periode_mvt == "mois":
            mouvements_grouped = \
            mouvements_df.groupby([mouvements_df["Date"].dt.to_period("M").dt.to_timestamp(), "Type"])[
                "Quantité"].sum().reset_index()
        else:
            mouvements_grouped = mouvements_df.groupby([mouvements_df["Date"].dt.year, "Type"])[
                "Quantité"].sum().reset_index()

        fig_mouvements = px.line(mouvements_grouped, x="Date", y="Quantité", color="Type",
                                 title=f"Évolution des mouvements par {periode_mvt}")
        st.plotly_chart(fig_mouvements)

    # Graphique alertes
    if not produits_alerte.empty:
        st.subheader("⚠️ Produits en alerte")
        fig_alerte = px.bar(produits_alerte, x="Nom Produit", y="Quantité",
                            title="Produits en alerte de stock")
        fig_alerte.add_scatter(x=produits_alerte["Nom Produit"], y=produits_alerte["Seuil Alerte"],
                               name="Seuil d'alerte", mode="lines")
        st.plotly_chart(fig_alerte)

# Onglet Produits
elif menu == "📦 Produits":
    st.header("📦 Liste des Produits")
    st.dataframe(st.session_state.produits_df)

    st.subheader("➕ Ajouter un produit")
    with st.form("add_product_form"):
        nom = st.text_input("Nom du produit", key="add_nom")
        cat = st.text_input("Catégorie", key="add_cat")
        prix = st.number_input("Prix unitaire", min_value=0, key="add_prix")
        quantite = st.number_input("Quantité", min_value=0, key="add_quantite")
        seuil = st.number_input("Seuil d'alerte", min_value=0, key="add_seuil")
        submitted = st.form_submit_button("Ajouter")

        if submitted and nom:
            produits_df = st.session_state.produits_df
            mouvements_df = st.session_state.mouvements_df
            new_id = produits_df["ID"].max() + 1 if not produits_df.empty else 1
            date_ajout = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nouveau_produit = pd.DataFrame([{
                "ID": new_id,
                "Nom Produit": nom,
                "Catégorie": cat,
                "Prix Unitaire": prix,
                "Quantité": quantite,
                "Seuil Alerte": seuil,
                "Date Ajout": date_ajout
            }])
            produits_df = pd.concat([produits_df, nouveau_produit], ignore_index=True)
            st.session_state.produits_df = produits_df
            save_data(produits_df, mouvements_df)
            st.success(f"✅ Produit '{nom}' ajouté avec succès.")
            
            # Réinitialiser le formulaire après ajout
            st.session_state["add_nom"] = ""
            st.session_state["add_cat"] = ""
            st.session_state["add_prix"] = 0
            st.session_state["add_quantite"] = 0
            st.session_state["add_seuil"] = 0

    st.subheader("✏️ Modifier un produit")
    with st.form("edit_product_form"):
        produits_df = st.session_state.produits_df
        produit_to_edit = st.selectbox("Sélectionner un produit à modifier", produits_df["Nom Produit"])
        nom = st.text_input("Nom du produit", key="edit_nom", value=produit_to_edit)
        cat = st.text_input("Catégorie", key="edit_cat")
        prix = st.number_input("Prix unitaire", min_value=0, key="edit_prix")
        quantite = st.number_input("Quantité", min_value=0, key="edit_quantite")
        seuil = st.number_input("Seuil d'alerte", min_value=0, key="edit_seuil")
        submitted = st.form_submit_button("Modifier")

        if submitted and produit_to_edit:
            idx = produits_df[produits_df["Nom Produit"] == produit_to_edit].index[0]
            produits_df.at[idx, "Nom Produit"] = nom
            produits_df.at[idx, "Catégorie"] = cat
            produits_df.at[idx, "Prix Unitaire"] = prix
            produits_df.at[idx, "Quantité"] = quantite
            produits_df.at[idx, "Seuil Alerte"] = seuil
            st.session_state.produits_df = produits_df
            save_data(produits_df, st.session_state.mouvements_df)
            st.success(f"✅ Produit '{produit_to_edit}' modifié avec succès.")

# Onglet Entrée / Sortie
elif menu == "➕ Entrée / ➖ Sortie":
    st.header("➕ Entrée / ➖ Sortie")
    produits_df = st.session_state.produits_df
    mouvements_df = st.session_state.mouvements_df

    st.subheader("Ajouter un mouvement")
    with st.form("mvt_form"):
        type_mvt = st.selectbox("Type de mouvement", ["Entrée", "Sortie"])
        produit_options = produits_df["Nom Produit"].tolist() if not produits_df.empty else []
        produit = st.selectbox("Produit", produit_options) if produit_options else st.text_input(
            "Produit (aucun produit disponible)")
        quantite = st.number_input("Quantité", min_value=1)
        commentaire = st.text_input("Commentaire")
        submitted = st.form_submit_button("Valider")

        if submitted and produit in produit_options:
            date = datetime.now().strftime("%Y-%m-%d")
            new_id = mouvements_df["ID"].max() + 1 if not mouvements_df.empty else 1
            nouveau_mvt = pd.DataFrame([{
                "ID": new_id,
                "Date": date,
                "Produit": produit,
                "Type": type_mvt,
                "Quantité": quantite,
                "Commentaire": commentaire
            }])
            mouvements_df = pd.concat([mouvements_df, nouveau_mvt], ignore_index=True)

            idx = produits_df[produits_df["Nom Produit"] == produit].index[0]
            if type_mvt == "Entrée":
                produits_df.at[idx, "Quantité"] += quantite
            else:
                if produits_df.at[idx, "Quantité"] >= quantite:
                    produits_df.at[idx, "Quantité"] -= quantite
                else:
                    st.error(
                        f"⚠️ Stock insuffisant ! Il ne reste que {produits_df.at[idx, 'Quantité']} unités du produit {produit}.")
                    st.stop()

            st.session_state.produits_df = produits_df
            st.session_state.mouvements_df = mouvements_df
            save_data(produits_df, mouvements_df)
            st.success("✅ Mouvement enregistré avec succès.")

    st.subheader("📜 Historique des mouvements")

    # Filtres pour l'historique
    col1, col2, col3 = st.columns(3)
    with col1:
        filtre_type = st.selectbox("Filtrer par type", ["Tous", "Entrée", "Sortie"])

    with col2:
        produits_liste = ["Tous"] + produits_df["Nom Produit"].unique().tolist()
        filtre_produit = st.selectbox("Filtrer par produit", produits_liste)

    with col3:
        date_debut = st.date_input("Date de début", datetime.now() - timedelta(days=30))
        date_fin = st.date_input("Date de fin", datetime.now())

    # Application des filtres
    filtered_mouvements = mouvements_df.copy()
    filtered_mouvements["Date"] = pd.to_datetime(filtered_mouvements["Date"])

    if filtre_type != "Tous":
        filtered_mouvements = filtered_mouvements[filtered_mouvements["Type"] == filtre_type]

    if filtre_produit != "Tous":
        filtered_mouvements = filtered_mouvements[filtered_mouvements["Produit"] == filtre_produit]

    filtered_mouvements = filtered_mouvements[
        (filtered_mouvements["Date"].dt.date >= date_debut) &
        (filtered_mouvements["Date"].dt.date <= date_fin)
        ]

    st.dataframe(filtered_mouvements)

# Onglet Exportation
elif menu == "📁 Exportation":
    st.header("📁 Exporter les données")
    produits_df = st.session_state.produits_df
    mouvements_df = st.session_state.mouvements_df

    st.download_button(
        label="📥 Télécharger Produits (CSV)",
        data=produits_df.to_csv(index=False).encode('utf-8'),
        file_name="produits.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📥 Télécharger Mouvements (CSV)",
        data=mouvements_df.to_csv(index=False).encode('utf-8'),
        file_name="mouvements.csv",
        mime="text/csv"
    )

    # Exporter tout en Excel
    data_excel = export_excel(produits_df, mouvements_df)
    st.download_button(
        label="📥 Télécharger toutes les données (Excel)",
        data=data_excel,
        file_name="donnees_stock_complet.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Options d'exportation avancées
    st.subheader("Exportation avancée")

    periode_export = st.selectbox("Période pour les recettes", ["jour", "mois", "année"])
    recettes_df = calculer_recettes(mouvements_df, produits_df, periode_export)

    if not recettes_df.empty:
        data_rapport = export_excel(produits_df, mouvements_df, recettes_df)
        st.download_button(
            label=f"📥 Télécharger rapport complet avec recettes par {periode_export} (Excel)",
            data=data_rapport,
            file_name=f"rapport_complet_{periode_export}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Onglet Réinitialiser Stock
elif menu == "⚙️ Réinitialiser Stock":
    st.header("⚙️ Réinitialiser le stock")

    if st.session_state.role == "admin":
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Réinitialiser les quantités")
            st.warning(
                "⚠️ Cette action mettra à zéro toutes les quantités en stock mais conservera les produits et l'historique.")
            if st.button("♻️ Réinitialiser le stock à zéro"):
                initialiser_stock()

        with col2:
            st.subheader("Purger toutes les données")
            st.error(
                "⚠️ ATTENTION ! Cette action supprimera définitivement tous les produits, mouvements et recettes !")

            # Double confirmation pour éviter les erreurs
            confirmation = st.checkbox("Je comprends que cette action est irréversible")

            if confirmation:
                if st.button("🗑️ PURGER TOUTES LES DONNÉES"):
                    purger_donnees()
    else:
        st.error("⛔ Accès refusé. Vous devez être administrateur pour accéder à cette page.")
