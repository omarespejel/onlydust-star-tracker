import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import pycountry
import streamlit as st
import yaml

# Use built-in json module instead of orjson
pio.json.config.default_engine = "json"


def load_config():
    with open("config.yaml", "r") as file:
        return yaml.safe_load(file)


def load_and_process_data(config):
    # Read the CSV data using the path from config
    data_path = Path(config["data"]["source_path"])
    if not data_path.exists():
        st.error(f"Data file not found at {data_path}")
        st.stop()

    df = pd.read_csv(data_path)

    # Clean and process data
    df["total_rewarded_usd_amount"] = df["total_rewarded_usd_amount"].fillna(0)
    df["pr_count"] = df["pr_count"].fillna(0)

    # Calculate cost per PR
    df["cost_per_pr"] = np.where(
        df["pr_count"] > 0,
        df["total_rewarded_usd_amount"] / df["pr_count"],
        df["total_rewarded_usd_amount"],  # If no PRs, use total reward as cost
    )

    # Determine developer category based on config
    def get_developer_category(pr_count):
        categories = config["developer_categories"]
        if pr_count <= categories["beginner"]["max_prs"]:
            return "Beginner"
        elif pr_count <= categories["rising_star"]["max_prs"]:
            return "Rising Star"
        elif pr_count <= categories["established"]["max_prs"]:
            return "Established Developer"
        elif pr_count <= categories["senior"]["max_prs"]:
            return "Senior Contributor"
        else:
            return "Elite Developer"

    df["developer_category"] = df["pr_count"].apply(get_developer_category)

    # Determine if developer is Starknet-exclusive
    df["is_starknet_exclusive"] = df["ecosystems"].apply(
        lambda x: True
        if isinstance(x, str) and "Starknet" in x and "," not in x
        else False
    )

    # Clean country codes
    df["country"] = df["country"].fillna("Unknown")

    # Convert ISO-2 country codes to country names
    def country_code_to_name(code):
        try:
            if code == "Unknown":
                return "Unknown"
            else:
                return pycountry.countries.get(alpha_2=code.strip()).name
        except:
            return "Unknown"

    df["country_name"] = df["country"].apply(country_code_to_name)

    # Ensure 'languages', 'projects', and 'categories' columns are lists
    df["languages"] = (
        df["languages"]
        .fillna("")
        .apply(lambda x: [lang.strip() for lang in str(x).split(",") if lang.strip()])
    )
    df["projects"] = (
        df["projects"]
        .fillna("")
        .apply(lambda x: [proj.strip() for proj in str(x).split(",") if proj.strip()])
    )
    df["categories"] = (
        df["categories"]
        .fillna("")
        .apply(lambda x: [cat.strip() for cat in str(x).split(",") if cat.strip()])
    )

    # Set the contacts file path
    contacts_dir = Path("data/generated")
    contacts_dir.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
    contacts_file = contacts_dir / "contacts.csv"

    if contacts_file.exists():
        contacts_df = pd.read_csv(contacts_file)
    else:
        contacts_df = pd.DataFrame(columns=["Developer", "Contact", "Contacted"])

    # Merge contact status into df
    df = df.merge(contacts_df, how="left", left_on="contributor", right_on="Developer")
    df["Contact"] = df["Contact"].fillna(False)
    df["Contacted"] = df["Contacted"].fillna(False)

    return df


def save_contacts(df):
    contacts_df = df[["contributor", "Contact", "Contacted"]].rename(
        columns={"contributor": "Developer"}
    )
    contacts_file = Path("data/generated/contacts.csv")
    contacts_df.to_csv(contacts_file, index=False)


def main():
    # Load configuration
    config = load_config()

    # Set page configuration
    st.set_page_config(
        page_title=config["app"]["title"],
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Load and process data
    df = load_and_process_data(config)

    # Sidebar filters
    st.sidebar.header("Filters")

    # Language filter
    all_languages = sorted(set([lang for langs in df["languages"] for lang in langs]))
    selected_languages = st.sidebar.multiselect(
        "Select Programming Languages", all_languages
    )

    # Category filter
    all_categories = sorted(set([cat for cats in df["categories"] for cat in cats]))
    selected_categories = st.sidebar.multiselect("Select Categories", all_categories)

    # Project filter
    all_projects = sorted(set([proj for projs in df["projects"] for proj in projs]))
    selected_projects = st.sidebar.multiselect("Select Projects", all_projects)

    # Apply filters
    filtered_df = df.copy()
    if selected_languages:
        filtered_df = filtered_df[
            filtered_df["languages"].apply(
                lambda langs: any(lang in langs for lang in selected_languages)
            )
        ]
    if selected_categories:
        filtered_df = filtered_df[
            filtered_df["categories"].apply(
                lambda cats: any(cat in cats for cat in selected_categories)
            )
        ]
    if selected_projects:
        filtered_df = filtered_df[
            filtered_df["projects"].apply(
                lambda projs: any(proj in projs for proj in selected_projects)
            )
        ]

    # Organize content into tabs
    tab1, tab2 = st.tabs(["Overview", "Developers and Projects"])

    with tab1:
        # Display header
        st.title(config["app"]["title"])
        st.caption(f"Data as of {config['data']['timestamp']}")

        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Developers", len(filtered_df))
        with col2:
            st.metric("Total PRs", int(filtered_df["pr_count"].sum()))
        with col3:
            avg_cost = filtered_df["cost_per_pr"].mean()
            st.metric("Average Cost per PR", f"${avg_cost:,.2f}")
        with col4:
            st.metric(
                "Total Investment",
                f"${filtered_df['total_rewarded_usd_amount'].sum():,.2f}",
            )

        # Developer Categories Distribution
        st.subheader("Developer Distribution by Category")
        st.write(
            "This chart shows the distribution of developers across different categories based on the number of pull requests they have made."
        )
        category_counts = filtered_df["developer_category"].value_counts().reset_index()
        category_counts.columns = ["Category", "Count"]
        fig_categories = px.bar(
            category_counts,
            x="Category",
            y="Count",
            color="Category",
            labels={"Count": "Number of Developers"},
            title="Developers by Category",
        )
        st.plotly_chart(fig_categories)

        # World Map of Investment
        st.subheader("Global Investment Distribution")
        st.write(
            "This map illustrates the total investment in USD distributed across different countries."
        )
        country_investment = (
            filtered_df.groupby("country_name")["total_rewarded_usd_amount"]
            .sum()
            .reset_index()
        )
        fig_map = px.choropleth(
            country_investment,
            locations="country_name",
            locationmode="country names",
            color="total_rewarded_usd_amount",
            hover_name="country_name",
            color_continuous_scale="Plasma",
            labels={"total_rewarded_usd_amount": "Total Investment (USD)"},
            projection="natural earth",
            title="Investment Distribution Across the Globe",
        )
        fig_map.update_layout(
            margin={"r": 0, "t": 50, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="Total Investment (USD)"),
        )
        st.plotly_chart(fig_map)

        # Network Distribution
        st.subheader("Developer Network Distribution")
        st.write(
            "This pie chart shows the focus of developers on Starknet exclusively or across multiple chains."
        )
        network_dist = filtered_df["is_starknet_exclusive"].value_counts()
        network_labels = [
            "Starknet Only" if val else "Multi-chain" for val in network_dist.index
        ]
        fig_pie = px.pie(
            values=network_dist.values,
            names=network_labels,
            title="Developer Network Focus",
        )
        st.plotly_chart(fig_pie)

    with tab2:
        # Developer Details
        st.subheader("Developer Details")

        # Developer Category Filter
        developer_categories = sorted(filtered_df["developer_category"].unique())
        selected_dev_categories = st.multiselect(
            "Filter by Developer Category", developer_categories
        )

        developer_table = filtered_df[
            [
                "contributor",
                "developer_category",
                "total_rewarded_usd_amount",
                "pr_count",
                "cost_per_pr",
                "country_name",
                "Contact",
                "Contacted",
            ]
        ].rename(
            columns={
                "contributor": "Developer",
                "developer_category": "Category",
                "total_rewarded_usd_amount": "Total Rewards (USD)",
                "pr_count": "Pull Requests",
                "cost_per_pr": "Cost per PR (USD)",
                "country_name": "Country",
                "Contact": "Contact",
                "Contacted": "Contacted",
            }
        )

        # Apply developer category filter
        if selected_dev_categories:
            developer_table = developer_table[
                developer_table["Category"].isin(selected_dev_categories)
            ]

        # Display editable developer table using st.data_editor
        edited_table = st.data_editor(
            developer_table,
            use_container_width=True,
            num_rows="dynamic",
            key="developer_table_editor",
        )

        # Update contacts when the table is edited
        if "developer_table_editor" in st.session_state:
            # Update the contacts data
            contacts_df = edited_table[["Developer", "Contact", "Contacted"]]
            contacts_file = Path("data/generated/contacts.csv")
            contacts_df.to_csv(contacts_file, index=False)
            st.success("Contacts updated successfully!")

        # Investment by Category
        st.subheader("Investment by Category")
        st.write(
            "This pie chart shows the percentage of the total investment assigned to different categories such as DeFi, Infrastructure, etc."
        )
        category_investment = (
            filtered_df.explode("categories")
            .groupby("categories")
            .agg({"total_rewarded_usd_amount": "sum"})
            .reset_index()
        )
        total_investment = category_investment["total_rewarded_usd_amount"].sum()
        category_investment["percentage"] = (
            category_investment["total_rewarded_usd_amount"] / total_investment
        ) * 100

        fig_category = px.pie(
            category_investment,
            values="total_rewarded_usd_amount",
            names="categories",
            title="Percentage of Total Investment by Category",
            labels={
                "categories": "Category",
                "total_rewarded_usd_amount": "Total Investment (USD)",
            },
            hover_data=["percentage"],
        )
        st.plotly_chart(fig_category)

        # Investment by Programming Language
        st.subheader("Investment by Programming Language")
        st.write(
            "This bar chart displays the total investment and average cost per PR for each programming language, ordered from highest to lowest investment."
        )
        language_investment = (
            filtered_df.explode("languages")
            .groupby("languages")
            .agg({"total_rewarded_usd_amount": "sum", "pr_count": "sum"})
            .reset_index()
        )
        language_investment["avg_cost_per_pr"] = (
            language_investment["total_rewarded_usd_amount"]
            / language_investment["pr_count"]
        )
        # Sort the data
        language_investment = language_investment.sort_values(
            "total_rewarded_usd_amount", ascending=False
        )
        fig_lang = px.bar(
            language_investment,
            x="languages",
            y="total_rewarded_usd_amount",
            color="avg_cost_per_pr",
            labels={
                "total_rewarded_usd_amount": "Total Investment (USD)",
                "languages": "Programming Language",
                "avg_cost_per_pr": "Average Cost per PR (USD)",
            },
            title="Total Investment by Programming Language",
            color_continuous_scale="Viridis",
        )
        fig_lang.update_layout(
            xaxis_title="Programming Language",
            yaxis_title="Total Investment (USD)",
            coloraxis_colorbar=dict(
                title="Avg Cost per PR (USD)",
                thicknessmode="pixels",
                thickness=15,
                lenmode="pixels",
                len=300,
                xpad=10,
                yanchor="middle",
                y=0.5,
            ),
        )
        st.plotly_chart(fig_lang)

        # Investment by Project
        st.subheader("Investment by Project")
        st.write(
            "This bar chart shows the total investment and average cost per PR for each project, ordered from highest to lowest investment."
        )
        project_investment = (
            filtered_df.explode("projects")
            .groupby("projects")
            .agg({"total_rewarded_usd_amount": "sum", "pr_count": "sum"})
            .reset_index()
        )
        project_investment["avg_cost_per_pr"] = (
            project_investment["total_rewarded_usd_amount"]
            / project_investment["pr_count"]
        )
        # Sort the data
        project_investment = project_investment.sort_values(
            "total_rewarded_usd_amount", ascending=False
        )
        fig_project = px.bar(
            project_investment,
            x="projects",
            y="total_rewarded_usd_amount",
            color="avg_cost_per_pr",
            labels={
                "total_rewarded_usd_amount": "Total Investment (USD)",
                "projects": "Project",
                "avg_cost_per_pr": "Average Cost per PR (USD)",
            },
            title="Total Investment by Project",
            color_continuous_scale="Cividis",
        )
        fig_project.update_layout(
            xaxis_title="Project",
            yaxis_title="Total Investment (USD)",
            xaxis={"categoryorder": "total descending"},
            coloraxis_colorbar=dict(
                title="Avg Cost per PR (USD)",
                thicknessmode="pixels",
                thickness=15,
                lenmode="pixels",
                len=300,
                xpad=10,
                yanchor="middle",
                y=0.5,
            ),
        )
        st.plotly_chart(fig_project)

        # Top Contributors
        st.subheader("Top Contributors by Total Rewards")
        st.write(
            "This bar chart displays the top 50 contributors based on the total rewards they have received."
        )
        top_contributors = filtered_df.nlargest(50, "total_rewarded_usd_amount")
        fig_top_contributors = px.bar(
            top_contributors,
            x="contributor",
            y="total_rewarded_usd_amount",
            labels={
                "total_rewarded_usd_amount": "Total Rewards (USD)",
                "contributor": "Contributor",
            },
            title="Top 50 Contributors",
        )
        fig_top_contributors.update_layout(
            xaxis_title="Contributor",
            yaxis_title="Total Rewards (USD)",
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_top_contributors)


if __name__ == "__main__":
    main()
