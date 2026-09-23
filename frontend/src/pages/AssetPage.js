import React, { useEffect, useState } from "react";
import { getIntro, getOutro } from "../api/apiService";
import { SearchInput } from "../components/ui/SearchInput";
import { SmallTable } from "../components/SmallTable";
import { AssetCreationModal } from "../components/AssetCreationModal";
import { createIntro, createOutro } from "../api/apiService";
import { deleteIntro, deleteOutro } from "../api/apiService";
import { useDebounce } from "../hooks/useDebounce";

export const AssetPage = () => {
  const [intros, setIntros] = useState([]);
  const [outros, setOutros] = useState([]);
  const [showIntroModal, setShowIntroModal] = useState(false);
  const [showOutroModal, setShowOutroModal] = useState(false);
  const [searchIntro, setSearchIntro] = useState(null);
  const [searchOutro, setSearchOutro] = useState(null);

  const debouncedSearchIntroTerm = useDebounce(searchIntro, 500);
  const debouncedSearchOutroTerm = useDebounce(searchOutro, 500);
  useEffect(() => {
    getIntro(debouncedSearchIntroTerm).then((response) => {
      setIntros(response);
    });
  }, [debouncedSearchIntroTerm]);

  useEffect(() => {
    getOutro(debouncedSearchOutroTerm).then((response) => {
      setOutros(response);
    });
  }, [debouncedSearchOutroTerm]);

  return (
    <>
      <AssetCreationModal
        showModal={showIntroModal}
        setShowModal={setShowIntroModal}
        nameh1="Intro"
        ApiCall={createIntro}
        setItems={setIntros}
      />
      <AssetCreationModal
        showModal={showOutroModal}
        setShowModal={setShowOutroModal}
        nameh1="Outro"
        ApiCall={createOutro}
        setItems={setOutros}
      />

      <div className="p-4 md:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="flex flex-col bg-white dark:bg-gray-800 dark:border dark:border-gray-700 rounded-lg shadow p-4">
            <div className="flex flex-wrap gap-2 justify-between items-center mb-4 w-full">
              <h2 className="text-xl font-bold">Intros</h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => { setShowIntroModal(true); }}
                  className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
                >
                  Create
                </button>
                <SearchInput placeholder="Search Intros" setVal={setSearchIntro} />
              </div>
            </div>
            <SmallTable data={intros} setData={setIntros} deleteFunction={deleteIntro} />
          </div>

          <div className="flex flex-col bg-white dark:bg-gray-800 dark:border dark:border-gray-700 rounded-lg shadow p-4">
            <div className="flex flex-wrap gap-2 justify-between items-center mb-4 w-full">
              <h2 className="text-xl font-bold">Outros</h2>
              <div className="flex items-center space-x-2">
                <button
                  onClick={(e) => { setShowOutroModal(true); }}
                  className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
                >
                  Create
                </button>
                <SearchInput placeholder="Search Outros" setVal={setSearchOutro} />
              </div>
            </div>
            <SmallTable data={outros} setData={setOutros} deleteFunction={deleteOutro} />
          </div>
        </div>
      </div>
    </>
  );
};
