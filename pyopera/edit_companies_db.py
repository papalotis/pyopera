import streamlit as st

from pyopera.common import CompanyModel
from pyopera.streamlit_common import (
    COMPANIES_INTERFACE,
    load_db_companies,
)


def upload_to_db(company: str, company_name: str, key: str | None):
    try:
        kwargs = dict(short_name=company, name=company_name)
        if key is not None:
            kwargs["key"] = key

        new_entry = CompanyModel(**kwargs)

        COMPANIES_INTERFACE.put_db(new_entry)
    except Exception as e:
        import traceback

        traceback.print_exc()  # Prints the full traceback to stderr
        st.toast("An error occured during upload", icon=":material/error:")
        return

    st.toast("Updated database", icon=":material/cloud_sync:")


def delete_company(key: str):
    try:
        COMPANIES_INTERFACE.delete_item_db(key)
    except Exception as e:
        print(e)
        st.toast("An error occured during deletion", icon=":material/error:")
        return

    st.toast("Deleted entry", icon=":material/delete:")


def run():
    title_element = st.empty()

    companies_db_list = load_db_companies(list_of_entries=True)
    assert isinstance(companies_db_list, list)

    if len(companies_db_list) > 0 and st.toggle("Registered Company "):
        company = st.selectbox(
            "Company Short Name",
            sorted(companies_db_list, key=lambda x: x.short_name),
            key="companyselectbox",
            format_func=lambda x: x.short_name,
        ).short_name
    else:
        company = st.text_input("Company Short Name", key="companytextinput").strip()

    is_new_entry = company not in {company_model.short_name for company_model in companies_db_list}

    title_verb = "Add" if is_new_entry else "Edit"
    title_element.markdown(f"# {title_verb} Company")

    company_entry = next(
        (company_model for company_model in companies_db_list if company_model.short_name == company),
        None,
    )

    company_name = st.text_input("Company Full Name", value=company_entry.name if company_entry is not None else None)

    button_text = "Add Company" if is_new_entry else "Update Company"
    st.button(
        button_text,
        on_click=upload_to_db,
        kwargs=dict(
            company=company,
            company_name=company_name,
            key=company_entry.key if company_entry is not None else None,
        ),
    )

    if not is_new_entry:
        st.divider()

        entry = next(
            (company_model for company_model in companies_db_list if company_model.short_name == company),
            None,
        )

        assert entry is not None

        st.write(entry)

        st.button("Delete Company", on_click=delete_company, kwargs=dict(key=entry.key))
